# GestolenDezeWeek.nl

Wekelijkse datalek-radar voor Nederland. Onderdeel van de **Check Don't Store** campagne.

## Deploy op Vercel (30 seconden)

```bash
npx vercel --prod
```

Of: sleep de map op [vercel.com/new](https://vercel.com/new) → klaar.
Geen build-step, geen framework, gewoon static HTML. Werkt ook 1-op-1 op Netlify / Cloudflare Pages / GitHub Pages.

## Wat je nu hebt

- ✅ Landingspagina met hero, preview, uitleg en vergelijking met HIBP
- ✅ Volledig werkende vinklijst van 40 NL diensten, gegroepeerd per categorie
- ✅ Selecties blijven bewaard in `localStorage` (terugkerende bezoeker ziet z'n keuzes weer)
- ✅ E-mail hand-off van hero naar vinklijst
- ✅ Validatie op e-mail + minstens 1 dienst
- ✅ Responsive (mobiel + desktop)
- ✅ Privacy-first: geen trackers, geen externe scripts behalve Google Fonts

## Wat je nog moet regelen (backend — 1 uur werk)

Zoek in `index.html` naar `TODO (backend)`. Daar moet een POST-request naar jouw signup-endpoint. Snelste opties:

1. **Formspree** — koppel het form, ontvang inschrijvingen in je mailbox (gratis tot 50/maand)
2. **Resend + Vercel Function** — maak `/api/signup.js`, hash de email, sla `{hash, services}` op in KV
3. **Mailchimp / Buttondown** — voeg subscriber toe + tag met geselecteerde services

Voor de **wekelijkse crawler** (Z-CERT, Tweakers, NOS): een simpele Vercel Cron Job (elke donderdag 09:00) die:
1. Nieuwe lekken ophaalt uit jouw bronnen
2. Per ingeschreven user checkt of hun geselecteerde services geraakt zijn
3. Gepersonaliseerde mail stuurt via Resend

## Tech

- 1 bestand. Geen dependencies. Geen build.
- Fonts: Fraunces (display) + IBM Plex Sans (body) + JetBrains Mono (data) via Google Fonts
- Ontwerp: Dutch editorial / investigatief journalistiek, niet de standaard SaaS-blauw look

## Bestandsstructuur

```
.
├── index.html    ← alles zit hier
└── README.md     ← dit bestand
```
