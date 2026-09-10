# Sito delle letture

Unica fonte dei contenuti: `Economia_letture_progressive.tex`. Non modificare a mano le pagine HTML generate.

## Attivazione una tantum

1. Verificare che repository e cronologia contengano soltanto materiale pubblicabile. Settings → General → Danger Zone → Change visibility → Public.
2. Settings → Pages → Build and deployment → Source → GitHub Actions.
3. Actions → Pubblica le letture → Run workflow (main).

In seguito ogni modifica al LaTeX, al convertitore o allo stile pubblica automaticamente il sito, solo se la conversione e le verifiche riescono. L'ultima pubblicazione riuscita resta disponibile durante la generazione.

## Conversione locale

Dipendenze: Python 3, Pandoc, XeLaTeX (standalone, TikZ, pgfplots e Latin Modern), pdftocairo.

Eseguire `python3 scripts/build_site.py`. Aprire `docs/index.html`, oppure servire `docs` con un server statico. Le formule usano MathML nativo; non occorrono CDN. L'arabo usa direzione RTL. I diagrammi TikZ vengono compilati individualmente in SVG, con shell escape disabilitato: non viene compilato il PDF del libretto.

Il convertitore gestisce la struttura di questo libretto, non ogni possibile documento LaTeX. Nuovi comandi non supportati bloccano la conversione anziché essere ignorati. Verificare sempre nuovi tipi di tabella o diagramma. L'HTML conserva i contenuti, non l'impaginazione a due colonne. La cronologia Git conserva le versioni precedenti.
