import createClient from 'openapi-fetch'

import type { paths } from './schema'

// Types are generated from the server's OpenAPI spec: run `just openapi` after API changes.
export const api = createClient<paths>({ baseUrl: '/' })
