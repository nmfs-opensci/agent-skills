# Browser access and CORS

**Provisional.** The server-side configuration below is verified: policies were
set and confirmed on two real GCS buckets on 2026-09-04. End-to-end rendering in
an actual browser is **not** yet verified. Keep those two claims apart when you
answer.

Reading a virtual Icechunk store from a browser needs three things to be true.
Only the first is about your store.

1. A JavaScript reader that understands Icechunk **and** virtual chunk payloads.
2. **CORS on every host the reader touches** — usually two, not one.
3. A chunk layout that survives being fetched over the public internet.

## The two-host trap, which is specific to virtual stores

In a virtual store metadata comes from the destination and data comes from the
source. A browser therefore makes cross-origin requests to **both**, and each
one needs its own CORS policy. They are frequently different buckets, different
projects, or different providers.

A store whose repository is CORS-enabled but whose source files are not will
open, show correct variable names, shapes and attributes, and then fail on every
data read. That failure looks like a broken store; it is a missing policy on the
other host.

Check both before concluding anything. When the store and the sources share one
bucket — convenient but not the general case — one policy covers both.

## What has to be in the policy

**`Range` is the load-bearing entry.** Every chunk read is an HTTP byte-range
request. `Range` is not a CORS-safelisted request header, so the browser sends a
preflight asking permission for it, and the server must allow it explicitly. Omit
it and every read fails with a generic CORS error that never mentions ranges —
which is why this costs people hours.

Also expose `Content-Range` so the client can interpret the 206. `Content-Type`
and `Content-Length` are already safelisted response headers; listing them is
harmless and conventional.

### Google Cloud Storage

Verified working on `noaa-oar-rfrom` and `noaa-oar-gobai`:

```json
[
  {
    "origin": ["*"],
    "method": ["HEAD", "GET"],
    "responseHeader": ["Range", "Content-Type", "Content-Length", "Content-Range"],
    "maxAgeSeconds": 3600
  }
]
```

```sh
gcloud storage buckets update gs://BUCKET --cors-file=cors.json
```

Two GCS specifics:

- **Do not put `OPTIONS` in `method`.** GCS answers preflight requests itself and
  echoes back exactly the methods configured. Google's documentation says not to
  list it. (Confirmed by comparing two buckets, one of which does list it — it is
  harmless, just unnecessary.)
- `responseHeader` does double duty: it is matched against the browser's
  `Access-Control-Request-Headers` on preflight, and it becomes
  `Access-Control-Expose-Headers` on the real response. That is why the
  *request* header `Range` appears in a field named for response headers.

### S3

Same idea, different spelling. `AllowedHeaders` is the field that must admit the
range request; `ExposeHeaders` is what JavaScript may read.

```json
[
  {
    "AllowedOrigins": ["*"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["Range", "Content-Type"],
    "ExposeHeaders": ["Content-Range", "Content-Length", "Accept-Ranges", "ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

```sh
aws s3api put-bucket-cors --bucket BUCKET --cors-configuration file://cors.json
```

Verify against current provider documentation. Non-AWS S3-compatible stores vary,
and a CDN in front of a bucket can strip or override CORS headers on `OPTIONS`
and on `206 Partial Content` responses independently of the bucket's own policy.

## When the user is not the bucket admin

This is the common case. Give them something they can forward without editing.
Fill in the bucket and origin, and say plainly what it does and does not grant.

> **Request: enable CORS for browser read access on `gs://BUCKET`**
>
> We are publishing a cloud-native dataset that browser applications read
> directly, without a server in between. Browsers block cross-origin requests
> unless the bucket returns CORS headers, so the data is currently unreadable
> from any web page even though it is public.
>
> Please apply this CORS policy:
>
> ```json
> [{"origin": ["*"],
>   "method": ["HEAD", "GET"],
>   "responseHeader": ["Range", "Content-Type", "Content-Length", "Content-Range"],
>   "maxAgeSeconds": 3600}]
> ```
>
> ```sh
> gcloud storage buckets update gs://BUCKET --cors-file=cors.json
> ```
>
> Notes:
> - **This grants no new access.** The objects are already publicly readable;
>   anyone can fetch them with `curl` today. CORS only tells browsers they are
>   allowed to do what other clients already can. Read-only: `GET` and `HEAD`,
>   no write methods.
> - **`Range` is required.** Clients read small byte ranges rather than whole
>   files. Without `Range` in `responseHeader`, every read fails.
> - The one real consideration is **egress**: with `origin: ["*"]` any web page
>   can cause its visitors' browsers to fetch from the bucket. If egress is
>   billed to your project rather than covered by an open-data program, tell us
>   and we will send a specific list of origins instead.

If they push back on `*`, offer exact origins — the application's host plus
`http://localhost:PORT` for development. Note that wildcard *subdomains*
(`https://*.example.com`) are not documented as supported by GCS, so a host with
per-deploy preview URLs is a reason to prefer `*`.

## Verifying, without a browser

Ask for the preflight and a ranged GET. This is what to run after an admin says
it is done, and what to run before claiming a store is browser-ready.

```sh
U="https://storage.googleapis.com/BUCKET/PATH/TO/OBJECT"

curl -s -D - -o /dev/null -X OPTIONS \
  -H "Origin: https://example.org" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: range" "$U" |
  grep -iE "^HTTP|access-control"

curl -s -D - -o /dev/null \
  -H "Origin: https://example.org" -H "Range: bytes=0-99" "$U" |
  grep -iE "^HTTP|access-control|content-range"
```

Want: preflight `200` with `access-control-allow-origin` and an
`access-control-allow-headers` that lists `range`; ranged GET `206` with
`access-control-allow-origin` and an `access-control-expose-headers` covering
`Content-Range`.

A bucket with no policy is unmistakable: the GET still returns `206`, and there
are no `access-control-*` headers anywhere.

**Curl is not a browser.** This proves the server returns the right headers. It
does not prove the reader works, the codecs are supported, or anything renders.
Do not upgrade a passing curl check into a claim of browser support — the same
rule this skill already applies to Python reads.

## When the bucket cannot be changed

Sometimes the data belongs to someone who will not or cannot set a policy. Three
fallbacks, best first:

1. **Mirror the data** to storage you control and set CORS there. Costs a copy
   and ongoing sync, and it is what a published web map usually ends up doing.
2. **A small proxy** that adds CORS headers. You now run a server, which is the
   thing a browser-native store was meant to avoid.
3. **A CORS-disabling browser extension**, for one person's own machine.

For the extension, be honest about what it is:

- It works only in **that person's browser**. It is a way to evaluate a dataset
  or demo something, never a way to publish. Anyone you send the link to hits the
  same wall.
- For a virtual store it must cover **both** hosts, the repository and the source
  files.
- It disables a real security control browser-wide. Advise a separate browser
  profile used only for this, not the everyday one.
- If you find yourself telling *users* to install one, the answer is a policy, a
  mirror, or a proxy — not an extension.

## Chunk layout is the next obstacle, not the last one

Getting CORS right makes a store reachable. It does not make it usable. A layout
tuned for point time series can be brutal for the whole-field reads a map viewer
performs, and a virtual store cannot rechunk.

For an exactly-tiling chunk `(T, 1, Y, X)` over `(time, level, lat, lon)`:

```
map read    = one field's bytes x T        <- depends only on the TIME chunk
series read = n_time x (Y * X * itemsize)  <- depends only on the SPATIAL tile area
```

They are orthogonal, and their product is fixed by chunk size alone, so no single
chunk grid serves both well at scale. Measured on a real store: a layout costing
~131 MB compressed to draw one 4 MB map field was simultaneously reading ~233 MB
to return one 6.9 KB point series — mediocre for both.

Say this before someone tunes for weeks. The resolution is not a cleverer chunk
shape; it is a second representation — keep full resolution virtual for analysis,
and add small materialized multiscale overviews chunked one-frame-per-chunk for
visualization. Downsampled overviews are cheap relative to the full store.

## What is verified, and what is not

**Verified**: that a missing policy blocks browsers; the exact GCS policy that
works and that `Range` is required; that GCS handles `OPTIONS` itself; that a
consumer stack exists (`zarrita` with `numcodecs.*` codecs, `icechunk-js` with
virtual chunk payloads and `gs://` → HTTPS rewriting); that curl confirms the
server side.

**Not verified**: rendering a virtual store end to end in a browser; the S3
policy above; any WASM read path; whether a given viewer handles extra dimensions
(a vertical level, say), needs its own catalog metadata, or reads CF time
correctly. Say so when asked, and propose the check rather than the answer.
