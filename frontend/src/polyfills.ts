// Safari < 15.4 lacks Object.hasOwn, which PrimeVue's styles call on load.
// Imported first in main.ts so it is in place before any PrimeVue module runs.
if (!Object.hasOwn) {
  Object.defineProperty(Object, 'hasOwn', {
    value: (object: object, key: PropertyKey) => Object.prototype.hasOwnProperty.call(object, key),
    configurable: true,
    writable: true,
  })
}
