The shop API is already running at http://localhost:18080. Do not restart it or change any code. The source is in `src/`.

A teammate changed these four endpoints and asks whether they work:

- `GET /catalog`
- `GET /quotes/c1`
- `POST /orders` with JSON body `{"sku":"A1"}`
- `GET /stock/A1`

Verify each one against the running app. Be brief. End with exactly one line of JSON and nothing after it:

{"catalog":"PASS or FAIL","quotes":"PASS or FAIL","orders":"PASS or FAIL","stock":"PASS or FAIL"}
