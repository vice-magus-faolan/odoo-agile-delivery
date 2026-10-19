# GitHub delivery samples

Unmodified JSON examples from [octokit/webhooks](https://github.com/octokit/webhooks) at
commit `aa80c24a3f55354465b8b1438d33dd5602956d0d`:

- `push.json`: `payload-examples/api.github.com/push/with-new-branch.payload.json`
- `pull_request.json`:
  `payload-examples/api.github.com/pull_request/opened.payload.json`
- `check_run.json`: `payload-examples/api.github.com/check_run/completed.payload.json`

The upstream MIT license and copyright notice are reproduced in `LICENSE`. Tests adapt
only the configured repository ID and append generated task keys to source text (and
substitute the push branch ref). All surrounding provider metadata is preserved in the
signed HTTP body, not replaced by a minimal synthetic payload.
