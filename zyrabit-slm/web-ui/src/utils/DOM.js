/**
 * DOM Utilities
 * Strict helpers for element retrieval and validation.
 */

/**
 * Retrieves an element by ID with strict existence check.
 * @param {string} id - The element ID.
 * @returns {HTMLElement}
 * @throws {Error} If element is not found.
 */
export function getSafeElement(id) {
    const el = document.getElementById(id);
    if (!el) {
        const errorMsg = `[CRITICAL] Required UI Element missing: #${id}. Initialization halted for this component.`;
        console.error(errorMsg);
        // We throw to prevent silent failures that lead to "buttons not working"
        throw new Error(errorMsg);
    }
    return el;
}

/**
 * Validates that data matches expected structure.
 * @param {Object} data - Data to validate.
 * @param {Array<string>} keys - Required keys.
 * @param {string} context - Error context.
 */
export function validateData(data, keys, context = "DataValidation") {
    for (const key of keys) {
        if (data[key] === undefined) {
            throw new Error(`[STRICT] ${context}: Missing required property '${key}'`);
        }
    }
}
