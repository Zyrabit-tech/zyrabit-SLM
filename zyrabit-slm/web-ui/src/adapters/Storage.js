/**
 * Storage Adapter
 * Handles persistence using sessionStorage (Shadow State).
 */
export class Storage {
    static save(key, data) {
        try {
            sessionStorage.setItem(`zyrabit_${key}`, JSON.stringify(data));
        } catch (e) {
            console.error("Storage Error:", e);
        }
    }

    static load(key) {
        try {
            const data = sessionStorage.getItem(`zyrabit_${key}`);
            return data ? JSON.parse(data) : null;
        } catch (e) {
            return null;
        }
    }

    static remove(key) {
        sessionStorage.removeItem(`zyrabit_${key}`);
    }
}
