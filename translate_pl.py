#!/usr/bin/env python3
"""Tłumaczenie tekstów Marvel Heroes EN -> PL, z ochroną znaczników.

Krok 1 - tłumaczenie (wznawialne, zapis co paczkę):
  python translate_pl.py translate --input eng_rus.json --output eng_pol.json --backend claude
  backendy: claude (ANTHROPIC_API_KEY, pip install anthropic)
            deepl  (DEEPL_API_KEY, pip install deepl)
            google (pip install deep-translator; wolne, limity, blokuje IP)
            argos  (pip install argostranslate; lokalnie, bez konta i limitów)
            local  (lokalny LLM, np. Qwen/Llama przez llama.cpp lub Ollama; bez zależności, patrz niżej)
            dummy  (bez sieci; dopisuje "[PL] " - do testu całego potoku w grze)
  opcje: --limit N, --batch N, --glossary glossary.json, --model NAZWA,
         --style-note plik.txt, --retry-errors, --translate-identical,
         --api-url URL (tylko local)

Backend local (Legion Go S, 4 GB VRAM) - serwer zgodny z OpenAI, np. llama.cpp (build Vulkan):
  llama-server -m Qwen3-4B-Instruct-2507-Q4_K_M.gguf -ngl 99 -c 4096 --port 8080
  python translate_pl.py translate --backend local --batch 25
  Ollama:  --api-url http://localhost:11434/v1 --model qwen3:4b-instruct-2507-q4_K_M

Ręcznie (paczki do tłumaczenia w czacie):
  python translate_pl.py export --count 200 --max-len 40   # -> batch.json (unikalne teksty, od najkrótszych)
  python translate_pl.py import --batch batch_pl.json      # dopisuje do eng_pol.json (z walidacją znaczników)

Krok 2 - wstawienie do plików rus_all_*.json (potem: mh_string_tool.py pack):
  python translate_pl.py apply --pol eng_pol.json --src rus_all_*.json --out-dir pl/
  opcje: --manual manual_variants_pl.json  (gotowe wpisy z polskimi wariantami, nadpisują resztę)

glossary.json: {"Danger Room": "Danger Room", "Shield": "Tarcza"} - stałe tłumaczenia terminów.
"""
import argparse, collections, json, os, re, sys, time

# znaczniki, które muszą przetrwać tłumaczenie bez zmian
MARKUP = re.compile(r'#/?\w+#|\$[^$\s][^$\n]*\$|<[^<>\n]{1,40}>|&\w+;')
LETTERS = re.compile(r'[^\W\d_]')
PLACEHOLDERS = {
    'brackets': (lambda i: f'[[{i}]]', re.compile(r'\[\[\s*(\d+)\s*\]\]')),
    'xml': (lambda i: f'<x id="{i}"/>', re.compile(r'<x\s+id="(\d+)"\s*/?>(?:</x>)?')),
}

# ---------------------------------------------------------------- pliki
def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def save(path, obj):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)

# ---------------------------------------------------------------- maskowanie (backendy MT)
class Masker:
    def __init__(self, glossary, style):
        self.make, self.rx = PLACEHOLDERS[style]
        parts = [MARKUP.pattern]
        terms = sorted(glossary, key=len, reverse=True)
        if terms:
            parts.append(r'\b(?:' + '|'.join(re.escape(t) for t in terms) + r')\b')
        self.pattern = re.compile('|'.join(parts))
        self.glossary = glossary

    def mask(self, text):
        toks = []
        def sub(m):
            toks.append(self.glossary.get(m.group(0), m.group(0)))
            return self.make(len(toks) - 1)
        return self.pattern.sub(sub, text), toks

    def has_text(self, masked):
        return bool(LETTERS.search(self.rx.sub('', masked)))

    def unmask(self, translated, toks):
        found = [int(i) for i in self.rx.findall(translated)]
        if sorted(found) != list(range(len(toks))):
            return None
        return self.rx.sub(lambda m: toks[int(m.group(1))], translated)

# ---------------------------------------------------------------- backendy
class DummyBackend:
    whole_entry, placeholder = False, 'brackets'
    def translate(self, texts):
        return ['[PL] ' + t for t in texts]

class GoogleBackend:
    """Darmowy Google przez deep-translator. Limit ~5 zapytań/s, dlatego linijki są łączone w paczki."""
    whole_entry, placeholder = False, 'brackets'
    MAX_CHARS, MAX_LINES, PAUSE = 4000, 25, 1.0
    def __init__(self):
        from deep_translator import GoogleTranslator
        self.t = GoogleTranslator(source='en', target='pl')
    def _call(self, text):
        for attempt in range(6):
            try:
                out = self.t.translate(text)
                time.sleep(self.PAUSE)
                return out or text
            except Exception as ex:
                wait = 30 * (attempt + 1)
                print(f'  Google: {str(ex)[:70]}... czekam {wait} s', file=sys.stderr)
                time.sleep(wait)
        raise RuntimeError('Google odmawia odpowiedzi - spróbuj później (godzina), z innego łącza '
                           'albo użyj --backend deepl / claude. Postęp jest zapisany.')
    def _long(self, text):                                   # pojedyncza linijka dłuższa niż limit
        parts, cur = [], ''
        for sent in re.split(r'(?<=[.!?]) ', text):
            if cur and len(cur) + len(sent) + 1 > self.MAX_CHARS:
                parts.append(cur); cur = sent
            else:
                cur = f'{cur} {sent}' if cur else sent
        parts.append(cur)
        return ' '.join(self._call(x) for x in parts)
    def translate(self, texts):
        out, i = [], 0
        while i < len(texts):
            group, size = [], 0
            while (i < len(texts) and len(group) < self.MAX_LINES
                   and size + len(texts[i]) + 1 <= self.MAX_CHARS):
                group.append(texts[i]); size += len(texts[i]) + 1; i += 1
            if not group:
                out.append(self._long(texts[i])); i += 1
                continue
            res = self._call('\n'.join(group)).split('\n') if len(group) > 1 else [self._call(group[0])]
            if len(res) != len(group):                       # Google zmienił liczbę linii -> pojedynczo
                res = [self._call(x) for x in group]
            out.extend(res)
        return out

class ArgosBackend:
    """Tłumaczenie lokalne (bez konta, bez limitów): pip install argostranslate. Model pobiera się raz."""
    whole_entry, placeholder = False, 'brackets'
    def __init__(self):
        import argostranslate.package as pkg
        import argostranslate.translate as tr
        def find():
            langs = tr.get_installed_languages()
            en = next((l for l in langs if l.code == 'en'), None)
            pl = next((l for l in langs if l.code == 'pl'), None)
            return en.get_translation(pl) if en and pl else None
        self.t = find()
        if self.t is None:
            print('Pobieram model angielski -> polski (jednorazowo)...')
            pkg.update_package_index()
            model = next(x for x in pkg.get_available_packages() if x.from_code == 'en' and x.to_code == 'pl')
            pkg.install_from_path(model.download())
            self.t = find()
        if self.t is None:
            raise RuntimeError('Nie udało się zainstalować modelu en->pl dla Argos.')
    def translate(self, texts):
        return [self.t.translate(x) for x in texts]

class DeepLBackend:
    whole_entry, placeholder = False, 'xml'
    def __init__(self):
        import deepl
        self.t = deepl.Translator(os.environ['DEEPL_API_KEY'])
    def translate(self, texts):
        res = self.t.translate_text(texts, source_lang='EN', target_lang='PL', tag_handling='xml',
                                    ignore_tags=['x'], preserve_formatting=True)
        return [r.text for r in res]

DEFAULT_CLAUDE_MODEL = 'claude-sonnet-5-5'
STYLE_DEFAULT = ('Imiona i pseudonimy bohaterów, złoczyńców i nazwy miejsc zostaw w oryginale (angielskie), '
                 'a opisy, zadania, interfejs i nazwy mocy tłumacz naturalnie.')

class ClaudeBackend:
    whole_entry, placeholder = True, None
    def __init__(self, model, glossary, style_note):
        import anthropic
        self.client, self.model = anthropic.Anthropic(), model
        gl = '\n'.join(f'- "{k}" => "{v}"' for k, v in glossary.items())
        self.system = (
            'Tłumaczysz teksty gry Marvel Heroes (akcyjne RPG o superbohaterach Marvela) z angielskiego na polski.\n'
            'Dostajesz obiekt JSON {id: tekst}. Zwróć WYŁĄCZNIE obiekt JSON z tymi samymi kluczami i przetłumaczonymi wartościami.\n'
            'Zasady:\n'
            '- Znaczniki zostaw dokładnie tak, jak są: #nazwa# i #/nazwa#, zmienne $...$, <...>, &lt; itp. '
            'Tłumacz tekst między znacznikami, ale nie zmieniaj, nie usuwaj i nie dodawaj znaczników.\n'
            '- Zachowaj te same podziały wierszy (\\n), spacje na początku i końcu oraz interpunkcję typu — przed podpisem cytatu.\n'
            '- Nie tłumacz identyfikatorów technicznych (np. condition0, powerreference1).\n'
            '- Teksty są krótkie i zwykle bez kontekstu - tłumacz zwięźle, w stylu gier akcji.\n'
            f'- {style_note}\n' + (f'Stałe tłumaczenia terminów:\n{gl}\n' if gl else ''))
    def translate_entries(self, items):
        msg = 'Przetłumacz wartości na polski.\n' + json.dumps(items, ensure_ascii=False)
        for attempt in range(3):
            try:
                r = self.client.messages.create(model=self.model, max_tokens=8000, system=self.system,
                                                messages=[{'role': 'user', 'content': msg}])
                return parse_json_reply(''.join(b.text for b in r.content if b.type == 'text'))
            except Exception as ex:
                print(f'  błąd API ({ex}); ponawiam...', file=sys.stderr)
                time.sleep(2 ** (attempt + 1))
        return {}

class LocalBackend:
    """Lokalny LLM przez API zgodne z OpenAI (llama.cpp llama-server, Ollama, LM Studio). Tylko stdlib.
    Każdy tekst idzie osobnym zapytaniem (małe modele psują wsadowy JSON); znaczniki są maskowane jako [[n]]."""
    whole_entry, placeholder = False, 'brackets'
    SHOTS = [
        ('[[0]]Shield[[1]] absorbs [[2]] damage for 5 seconds.',
         '[[0]]Shield[[1]] pochłania [[2]] obrażeń przez 5 sekund.'),
        ('Defeat 10 enemies in the Danger Room.',
         'Pokonaj 10 wrogów w Danger Room.'),
        ('Press [[0]] to open the map.',
         'Naciśnij [[0]], aby otworzyć mapę.'),
    ]
    def __init__(self, model, api_url, style_note):
        self.model, self.url = model, api_url.rstrip('/') + '/chat/completions'
        self.messages = [{'role': 'system', 'content': (
            'Tłumaczysz teksty gry Marvel Heroes (akcyjne RPG o superbohaterach Marvela) z angielskiego na polski.\n'
            'Zwróć WYŁĄCZNIE tłumaczenie, bez komentarzy i cudzysłowów.\n'
            'Znaczniki w postaci [[0]], [[1]] ... zostaw bez zmian, w tej samej liczbie; nie tłumacz ich ani nie dodawaj nowych.\n'
            'Tłumacz zwięźle, w stylu gier akcji.\n' + style_note)}]
        for en, pl in self.SHOTS:
            self.messages += [{'role': 'user', 'content': en}, {'role': 'assistant', 'content': pl}]
        try:                                                  # szybki test połączenia
            self._ask('Hello')
        except Exception as ex:
            raise RuntimeError(f'Brak odpowiedzi serwera LLM pod {self.url} ({ex}). Uruchom llama-server/Ollama '
                               f'albo podaj --api-url.')
    def _ask(self, text):
        import urllib.request
        body = {'model': self.model, 'temperature': 0.2, 'max_tokens': min(1024, max(64, len(text) * 3)),
                'messages': self.messages + [{'role': 'user', 'content': text}]}
        req = urllib.request.Request(self.url, json.dumps(body).encode('utf-8'),
                                     {'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=300) as r:
            out = json.load(r)['choices'][0]['message']['content'] or ''
        out = re.sub(r'<think>.*?</think>', '', out, flags=re.S).strip()   # Qwen3 w trybie myślenia
        out = re.sub(r'\s*\n\s*', ' ', out)
        if len(out) >= 2 and out[0] == out[-1] == '"' and not (text[0] == '"' and text[-1] == '"'):
            out = out[1:-1]
        return out
    def translate(self, texts):
        res = []
        for t in texts:
            out = self._ask(t)
            res.append(out if out else t)                     # pusty wynik -> zostaje oryginał
        return res

def parse_json_reply(text):
    text = re.sub(r'^```(?:json)?|```$', '', text.strip(), flags=re.M).strip()
    a, b = text.find('{'), text.rfind('}')
    try:
        obj = json.loads(text[a:b + 1])
        return obj if isinstance(obj, dict) else {}
    except ValueError:
        return {}

# ---------------------------------------------------------------- logika tłumaczenia
def should_skip(eng, rus, translate_identical):
    if not eng.strip() or not LETTERS.search(MARKUP.sub('', eng)):
        return True
    return eng == rus and not translate_identical

def markup_of(text):
    return collections.Counter(MARKUP.findall(text))

def valid_claude(eng, pol):
    return (isinstance(pol, str) and pol.strip() != '' and markup_of(eng) == markup_of(pol)
            and eng.count('\n') == pol.count('\n'))

def with_retry(fn, *args):
    for attempt in range(3):
        try:
            return fn(*args)
        except RuntimeError:
            raise
        except Exception as ex:
            print(f'  błąd tłumaczenia ({ex}); ponawiam...', file=sys.stderr)
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError('backend nie odpowiada')

def translate_chunk_claude(chunk, backend):
    res = backend.translate_entries({k: eng for k, eng in chunk})
    out = {}
    for k, eng in chunk:
        pol = res.get(k)
        if not valid_claude(eng, pol):                      # jedna próba pojedynczo
            pol = backend.translate_entries({k: eng}).get(k)
        out[k] = ({'eng': eng, 'pol': pol} if valid_claude(eng, pol)
                  else {'eng': eng, 'pol': '', 'error': 'znaczniki/podział wierszy się nie zgadzają'})
    return out

def piecewise(core, backend, masker, cache):
    """Awaryjnie: tekst między znacznikami tłumaczony osobno, znaczniki wstawiane z powrotem w tej samej kolejności."""
    segs, last = [], 0
    for m in masker.pattern.finditer(core):
        segs.append(('t', core[last:m.start()]))
        segs.append(('k', masker.glossary.get(m.group(0), m.group(0))))
        last = m.end()
    segs.append(('t', core[last:]))
    need = []
    for kind, txt in segs:
        t = txt.strip()
        if kind == 't' and t and LETTERS.search(t) and t not in cache and t not in need:
            need.append(t)
    if need:
        cache.update(zip(need, with_retry(backend.translate, need)))
    out = []
    for kind, txt in segs:
        t = txt.strip()
        if kind == 't' and t and LETTERS.search(t):
            lead, trail = txt[:len(txt) - len(txt.lstrip())], txt[len(txt.rstrip()):]
            out.append(lead + cache[t] + trail)
        else:
            out.append(txt)
    return ''.join(out)

def translate_chunk_mt(chunk, backend, masker, cache):
    plans, need = {}, {}
    for k, eng in chunk:
        plan = []
        for line in eng.split('\n'):
            lead, core, trail = re.match(r'^(\s*)(.*?)(\s*)$', line, re.S).groups()
            masked, toks = masker.mask(core)
            if masker.has_text(masked):
                if masked not in cache:
                    need[masked] = True
                plan.append((lead, masked, toks, trail, core))
            else:
                plan.append((lead, core, None, trail, core))
        plans[k] = plan
    need = list(need)
    for i in range(0, len(need), 40):
        part = need[i:i + 40]
        res = with_retry(backend.translate, part)
        if len(res) != len(part):
            raise RuntimeError('liczba wyników różni się od liczby zapytań')
        cache.update(zip(part, res))
    out = {}
    for k, eng in chunk:
        lines = []
        for lead, text, toks, trail, core in plans[k]:
            if toks is None:
                lines.append(lead + text + trail)
                continue
            fixed = masker.unmask(cache[text], toks)
            if fixed is None:                                   # model zgubił znacznik -> tłumacz kawałki osobno
                fixed = piecewise(core, backend, masker, cache)
            lines.append(lead + fixed + trail)
        out[k] = {'eng': eng, 'pol': '\n'.join(lines)}
    return out

def cmd_translate(a):
    data = load(a.input)
    out = load(a.output) if os.path.exists(a.output) else {}
    glossary = load(a.glossary) if a.glossary else {}
    style_note = open(a.style_note, encoding='utf-8').read().strip() if a.style_note else STYLE_DEFAULT
    if a.backend == 'claude':
        backend = ClaudeBackend(a.model, glossary, style_note)
    elif a.backend == 'local':
        backend = LocalBackend(a.model if a.model != DEFAULT_CLAUDE_MODEL else 'qwen', a.api_url, style_note)
    else:
        backend = {'deepl': DeepLBackend, 'google': GoogleBackend, 'argos': ArgosBackend, 'dummy': DummyBackend}[a.backend]()
    masker = None if backend.whole_entry else Masker(glossary, backend.placeholder)
    cache = {}
    todo = [(k, v['eng'], v['rus']) for k, v in data.items()
            if k != 'Invalid' and (k not in out or (a.retry_errors and out[k].get('error')))]
    if a.limit:
        todo = todo[:a.limit]
    print(f'do zrobienia: {len(todo)} wpisów')
    done, last_save = 0, time.time()
    try:
        for i in range(0, len(todo), a.batch):
            chunk = []
            for k, eng, rus in todo[i:i + a.batch]:
                if should_skip(eng, rus, a.translate_identical):
                    out[k] = {'eng': eng, 'pol': eng, 'skipped': True}
                else:
                    chunk.append((k, eng))
            if chunk:
                out.update(translate_chunk_claude(chunk, backend) if backend.whole_entry
                           else translate_chunk_mt(chunk, backend, masker, cache))
            done += len(todo[i:i + a.batch])
            if time.time() - last_save > 30:                    # zapis co ~30 s (plik jest duży)
                save(a.output, out)
                last_save = time.time()
                print(f'  {done}/{len(todo)}')
    finally:
        save(a.output, out)                                 # także po Ctrl+C / błędzie
    errs = sum(1 for v in out.values() if v.get('error'))
    print(f'gotowe. wpisów w pliku: {len(out)}, z błędem: {errs} (ponów: --retry-errors)')

# ---------------------------------------------------------------- wstawienie do JSON-ów gry
def cmd_apply(a):
    pol = load(a.pol)
    manual = load(a.manual) if a.manual else {}
    os.makedirs(a.out_dir, exist_ok=True)
    review, stats = [], collections.Counter()
    for src in a.src:
        obj = load(src)
        for k, e in obj['StringMap'].items():
            if k == 'Invalid':
                continue
            if k in manual:
                obj['StringMap'][k] = manual[k]
                stats['ręczne'] += 1
                continue
            p = pol.get(k)
            if p is None:
                stats['bez tłumaczenia (zostaje rosyjski)'] += 1
                continue
            text = p['pol'] or p['eng']                     # błąd tłumaczenia -> angielski, nie zepsuty tekst
            stats['błąd tłumaczenia (zostaje angielski)' if p.get('error') else
                  'bez zmian (puste/techniczne)' if p.get('skipped') or not p['eng'] else 'przetłumaczone'] += 1
            if e['Variants']:
                review.append({'id': k, 'eng': p['eng'], 'pol': text,
                               'rus_variants': [[v['FlagsConsumed'], v['String']] for v in e['Variants']]})
                for v in e['Variants']:
                    v['String'] = text                      # tymczasowo ten sam tekst we wszystkich wariantach
            e['String'] = text
        save(os.path.join(a.out_dir, os.path.basename(src)), obj)
    save(os.path.join(a.out_dir, 'variants_to_review.json'), review)
    print(dict(stats), f'| do ręcznego sprawdzenia (warianty): {len(review)} -> variants_to_review.json')

# ---------------------------------------------------------------- ręczne paczki (export / import)
def cmd_export(a):
    data = load(a.input)
    pol = load(a.pol) if os.path.exists(a.pol) else {}
    seen, batch = set(), {}
    for k, v in data.items():
        eng = v['eng']
        if k == 'Invalid' or k in pol or eng in seen or should_skip(eng, v['rus'], a.translate_identical):
            continue
        if a.max_len and len(eng) > a.max_len:
            continue
        if a.min_len and len(eng) < a.min_len:
            continue
        seen.add(eng)
        batch[k] = eng                                       # każdy tekst raz; import rozda go identycznym wpisom
    items = sorted(batch.items(), key=lambda kv: (len(kv[1]), kv[1])) if a.sort == 'len' else list(batch.items())
    items = items[a.skip:][:a.count] if a.count else items[a.skip:]
    save(a.out, dict(items))
    print(f'zapisano {len(items)} unikalnych tekstów do {a.out} (łącznie pasujących: {len(batch)})')

def cmd_import(a):
    data = load(a.input)
    pol = load(a.pol) if os.path.exists(a.pol) else {}
    batch = load(a.batch)
    by_eng = collections.defaultdict(list)
    for k, v in data.items():
        if k != 'Invalid' and k not in pol:
            by_eng[v['eng']].append(k)
    ok = bad = applied = 0
    for k, txt in batch.items():
        eng = data[k]['eng'] if k in data else None
        if eng is None or not valid_claude(eng, txt):
            print('  ODRZUCONE', k, repr(eng), '->', repr(txt)); bad += 1
            continue
        ok += 1
        for kk in by_eng.get(eng, [k]):
            pol[kk] = {'eng': eng, 'pol': txt}; applied += 1
    save(a.pol, pol)
    print(f'przyjęte teksty: {ok}, odrzucone: {bad}, wpisów uzupełnionych (z duplikatami): {applied}, razem w {a.pol}: {len(pol)}')

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    t = sub.add_parser('translate')
    t.add_argument('--input', default='eng_rus.json'); t.add_argument('--output', default='eng_pol.json')
    t.add_argument('--backend', choices=['claude', 'deepl', 'google', 'argos', 'local', 'dummy'], default='claude')
    t.add_argument('--model', default=DEFAULT_CLAUDE_MODEL); t.add_argument('--batch', type=int, default=25)
    t.add_argument('--limit', type=int); t.add_argument('--glossary'); t.add_argument('--style-note')
    t.add_argument('--api-url', default='http://localhost:8080/v1')
    t.add_argument('--retry-errors', action='store_true'); t.add_argument('--translate-identical', action='store_true')
    p = sub.add_parser('apply')
    p.add_argument('--pol', default='eng_pol.json'); p.add_argument('--src', nargs='+', required=True)
    p.add_argument('--out-dir', default='pl'); p.add_argument('--manual')
    e = sub.add_parser('export')
    e.add_argument('--input', default='eng_rus.json'); e.add_argument('--pol', default='eng_pol.json')
    e.add_argument('--out', default='batch.json'); e.add_argument('--count', type=int, default=200)
    e.add_argument('--skip', type=int, default=0); e.add_argument('--max-len', type=int); e.add_argument('--min-len', type=int)
    e.add_argument('--sort', choices=['len', 'none'], default='len'); e.add_argument('--translate-identical', action='store_true')
    i = sub.add_parser('import')
    i.add_argument('--input', default='eng_rus.json'); i.add_argument('--pol', default='eng_pol.json')
    i.add_argument('--batch', default='batch_pl.json')
    a = ap.parse_args()
    {'translate': cmd_translate, 'apply': cmd_apply, 'export': cmd_export, 'import': cmd_import}[a.cmd](a)

if __name__ == '__main__':
    main()
