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
