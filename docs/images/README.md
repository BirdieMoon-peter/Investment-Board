# Runtime screenshots

Captured from the running production build in an isolated demonstration database
on 2026-09-13, with the interface in Chinese. The database combines public historical
market snapshots with fixed test quotes for a five-security layout. It is separate
from the user's database and contains no personal holdings.

- `dashboard.jpg`: light-theme watchlist workspace, local filters, sortable prices,
  market strip and research sidebar. The displayed AI label comes from an explicitly
  simulated local response, not a real recommendation.
- `stock-detail.jpg`: dark-theme Ping An Bank research view with the three research
  groups, historical candlesticks/volume, quote context and fundamentals.
- `ai-settings.png`: direct capture of the light-theme settings drawer. The loopback
  address and model are test fixtures. No credential is displayed and the image
  does not claim an actual external connection test.

These are direct browser captures without compositing or generated UI. Main images
use a 1440x960 viewport; the AI configuration image captures the drawer element.
Quotes and dates are fixed snapshots and do not represent live prices or performance.
