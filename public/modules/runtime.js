/**
 * @typedef {Object} Asset
 * @property {string} id Stable asset identity used by favorites and assignments.
 * @property {string} name
 * @property {string} category
 * @property {string} categoryZh
 * @property {'material'|'normal'|'decal'} assetGroup
 * @property {Array<{name:string,channel:string,ext:string}>} maps
 * @property {string} [kind]
 *
 * @typedef {Object} AppContext
 * @property {Asset[]} assets
 * @property {Asset[]} filtered
 * @property {Map<string,Asset>} byId
 * @property {{favorites:string[],collections:Object[],recent:Array<string|Object>}} state
 * @property {string} token
 * @property {string} assetType
 * @property {string} category
 * @property {number} limit
 * @property {function(string, Object=): Promise<Object>} post
 * @property {function(): Promise<void>} load
 * @property {function(boolean=): void} renderResults
 * @property {function(): void} renderNav
 * @property {function(string): void} openDetail
 *
 * Explicit shared application interface; bootstrap wires state and services.
 * Feature factories receive the interface instead of reading script globals.
 */
/** @type {AppContext} */
export const app = /** @type {AppContext} */ ({});
