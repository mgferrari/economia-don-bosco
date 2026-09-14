# Sito e PDF delle letture

Le fonti dei contenuti sono i file HTML in `content/`. Non modificare a mano le pagine in `docs/`, perché vengono generate automaticamente.

## Attivazione una tantum

1. Verificare che repository e cronologia contengano soltanto materiale pubblicabile. Settings → General → Danger Zone → Change visibility → Public.
2. Settings → Pages → Build and deployment → Source → GitHub Actions.
3. Actions → Pubblica le letture → Run workflow (main).

In seguito ogni modifica ai contenuti HTML, al generatore o allo stile pubblica automaticamente sito e PDF, solo se tutte le verifiche riescono. L'ultima pubblicazione riuscita resta disponibile durante la generazione.

## Struttura

- `content/chapters/`: i quattordici capitoli, modificabili direttamente in HTML;
- `content/site.json`: ordine, numero e titolo dei capitoli;
- `content/sources.html`: bibliografia;
- `content/front-matter.html`: istruzioni iniziali del libretto;
- `web/style.css`: stile del sito;
- `web/print.css`: impaginazione A4 del PDF;
- `web/assets/`: grafici e immagini originali;
- `docs/`: sito e PDF generati.

Le citazioni nei capitoli usano la forma `<sup><a data-source="chiave"></a></sup>`. La chiave deve corrispondere a un elemento `id="src-chiave"` in `content/sources.html`; numero e collegamento vengono aggiunti automaticamente.

## Generazione locale

Creare un ambiente Python e installare `requirements.txt`. Poi eseguire:

```bash
python3 scripts/build_site.py
python3 scripts/build_pdf.py
```

Aprire `docs/index.html` per il sito oppure `docs/economia-leggere-e-capire.pdf` per il libretto. Le formule usano MathML nativo, i grafici sono SVG e non occorrono servizi esterni.

Il precedente sorgente LaTeX è conservato soltanto in `archive/` come copia storica. Non partecipa più alla generazione.
