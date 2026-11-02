# Spolszczenie do gry Marvel Heroes (wersja 1.52)

## Jak działa spolszczenie?

Paczka podmienia zasoby technicznego profilu językowego o kodzie **sg3** na tekst polski. Dzięki temu domyślna wersja angielska oraz pozostałe oficjalne języki pozostają nienaruszone, co pozwala na szybki powrót do oryginału w dowolnym momencie.

## Dlaczego wykorzystano kod sg3?

Gra Marvel Heroes oficjalnie obsługuje siedem języków: angielski, francuski, niemiecki, rosyjski, japoński, portugalski oraz hiszpański. Dodanie zupełnie nowego indeksu językowego wymagałoby modyfikacji pliku wykonywalnego (exe), silnika serwera oraz szeregu innych komponentów.

Kod **sg3** to techniczny profil językowy, który domyślnie zawiera tekst angielski. Zastąpienie go polskim tłumaczeniem daje kilka korzyści:

- Nie usuwa żadnego z pozostałych języków dostępnych w kliencie gry.
- Nie powoduje błędów po stronie serwera ani nagłego przełączenia gry na inny język.
- Pozostawia profil **eng** bez zmian, umożliwiając błyskawiczne przywrócenie wersji angielskiej.

## Ograniczenia

Spolszczenie obejmuje wyłącznie teksty przechowywane lokalnie i wyświetlane przez klienta gry. Część treści jest jednak pobierana bezpośrednio z serwera i pozostanie w języku oryginalnym. Dotyczy to między innymi:

- Nazw oraz opisów osiągnięć.
- Niestandardowych przedmiotów dodawanych przez administratorów serwerów (np. nowych przedmiotów OMEGA na serwerze TAHITI).

Obecnie serwery dysponują bazą tekstową w języku angielskim oraz rosyjskim. Wybór kodu **sg3** zabezpiecza graczy na wypadek dodania kolejnych tłumaczeń po stronie serwera — w przypadku braku obsługi wybranego kodu serwer zawsze domyślnie przesyła teksty w języku angielskim.

## Instalacja

1. **Pobranie plików:** Pobierz najnowszą paczkę ze spolszczeniem z zakładki **Releases**.
2. **Wgranie spolszczenia:** Wypakuj archiwum do głównego folderu gry i podmień wszystkie pliki (dla wersji Steam: *C:\Program Files (x86)\Steam\steamapps\common\Marvel Heroes*).
3. **Zmiana konfiguracji:** W pliku *savedLocaleSetting.txt* (w lokalizacji *shell:Personal\My Games\Marvel Heroes\MarvelGame\Config*) zmień wpis z **eng** na **sg3**.
4. **Zablokowanie zapisu:** We właściwościach pliku *savedLocaleSetting.txt* zaznacz opcję **Tylko do odczytu**, aby gra nie nadpisywała języka przy zmianie ustawień w menu.

## Podziękowania

Podziękowania dla **AlexBond2** za stworzenie rosyjskiego tłumaczenia, które posłużyło w tym projekcie jako baza do przygotowania spolszczenia.

- Profil GitHub: https://github.com/AlexBond2
- Repozytorium projektu: https://github.com/AlexBond2/MHRusLocalization


# Polish Localization for Marvel Heroes (Version 1.52)

## How does it work?

The package replaces the resources of the technical language profile **sg3** with Polish text. Thanks to this, the default English version and other official languages remain untouched, allowing you to quickly revert to the original language at any time.

## Why the sg3 code?

Marvel Heroes officially supports seven languages: English, French, German, Russian, Japanese, Portuguese, and Spanish. Adding a completely new language index would require modifying the executable file (exe), the server engine, and several other components.

The **sg3** code is a technical language profile that contains English text by default. Replacing it with the Polish translation offers several benefits:

- It does not remove any of the other languages available in the game client.
- It does not cause server-side issues or suddenly switch the game to another language.
- It leaves the **eng** profile unchanged, allowing an instant return to the English version.

## Limitations

The localization covers only texts stored locally and displayed by the game client. However, some content is fetched directly from the server and will remain in the original language. This includes:

- Achievement names and descriptions.
- Custom items added by server administrators (e.g., recent OMEGA items on the TAHITI server).

Currently, servers have text databases in English and Russian. Choosing the **sg3** code protects players in case additional translations are added on the server side — if the selected language code is missing on the server, the game always defaults to English.

## Installation

1. **Download files:** Download the latest localization package from the **Releases** tab.
2. **Extract files:** Extract the archive and overwrite all files in your main game folder (Steam version path: *C:\Program Files (x86)\Steam\steamapps\common\Marvel Heroes*).
3. **Update configuration:** Open *savedLocaleSetting.txt* (located in *shell:Personal\My Games\Marvel Heroes\MarvelGame\Config*) and change **eng** to **sg3**.
4. **Lock configuration file:** In the properties of *savedLocaleSetting.txt*, check the **Read-only** option to prevent the game from resetting the language when changing settings in the in-game menu.

## Credits

Special thanks to **AlexBond2** for creating the Russian localization, which served as the base for this Polish translation project.

- GitHub Profile: https://github.com/AlexBond2
- Project Repository: https://github.com/AlexBond2/MHRusLocalization
