# Third-party context and graph sources

## loop-engineering

- Upstream: <https://github.com/cobusgreyling/loop-engineering>
- Reviewed revision: `a6b41ab0351d67ffe3a77370a7f5807de7562ad6`
- License: MIT
- Use here: concepts only—bounded attempts, skills, durable sanitized state,
  maker/checker verification, deny rules, budgets, machine gates, and human
  stops. No upstream source code or templates were vendored.

## Graphify

- Reviewed local product: Graphify `0.9.46`
- Reviewed revision: `53b7f766ddb840f4bf046030f1fbbff9cddefdeb`
- License: Apache-2.0, with retained MIT-licensed legacy portions documented by
  its own license files
- Use here: optional local code-only architecture mapping through a restrictive
  repository skill. No Graphify source code or generated private graph is
  redistributed.

Graph outputs, reflections, query logs, and private run manifests stay
untracked. Source terms must be rechecked before a future version is adopted.
