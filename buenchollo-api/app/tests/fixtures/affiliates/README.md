# Fixtures sintéticas de redes de afiliación

**Todo lo de esta carpeta es inventado para tests.** No son productos, precios,
enlaces ni feeds reales de Awin, Tradedoubler ni de ninguna tienda; los
nombres llevan el prefijo `FIXTURE` y los IDs no corresponden a nada real.

El formato imita la documentación oficial consultada el 2026-11-08:

- `awin_feed_list.csv`: columnas de la *Product Feed List Download* de Awin.
- `awin_feed.csv`: columnas habituales del feed de publisher de Awin
  (`aw_product_id`, `merchant_deep_link`, `search_price`...). **Pendiente de
  contrastar con un feed real** cuando haya clave de feeds.
- `td_products.json`: forma de la respuesta de la Products API 1.0 de
  Tradedoubler (`products[].offers[].productUrl/sourceProductUrl/priceHistory`).
  **Pendiente de contrastar con una respuesta real** cuando haya token.
