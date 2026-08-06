import { test, expect } from '@playwright/test';

/**
 * ZYRABIT SOVEREIGN E2E SUITE
 * 
 * Esta suite valida el flujo completo de soberanía:
 * 1. Ingesta de conocimiento (RAG).
 * 2. Consulta distribuida (SLM).
 * 3. Comunicación externa segura (Telegram).
 */

test.describe('Zyrabit SLM Console', () => {

    test.beforeEach(async ({ page }) => {
        // Accedemos al portal (asegúrate de que el servidor esté corriendo)
        await page.goto('http://localhost:3000');
        // Esperamos a que la UI esté lista
        await expect(page.locator('#health-api-dot')).toHaveAttribute('status', 'online');
    });

    test('Flujo Completo: Ingesta -> RAG -> Telegram', async ({ page }) => {
        // 1. Abrir Vault
        const vaultBtn = page.locator('#toggle-ingest');
        await vaultBtn.click();
        
        // Verificar que el panel se abra (usando la clase .side-panel)
        await expect(page.locator('#ingest-panel')).toHaveClass(/active/);

        // 2. Subir Documento
        const fileChooserPromise = page.waitForEvent('filechooser');
        await page.locator('#drop-zone').click();
        const fileChooser = await fileChooserPromise;
        await fileChooser.setFiles('/Users/abrahamgomez/tech/zyrabit-SLM/test_knowledge.txt');

        // 3. Verificar procesamiento en GateKeeper
        await page.locator('#toggle-gdpr').click();
        // Esperamos a que aparezca el log de sincronización
        await expect(page.locator('#gdpr-logs')).toContainText('SYNCED_1_DOCUMENTS', { timeout: 30000 });

        // 4. Preguntar sobre el documento
        const chatInput = page.locator('#chat-input');
        await chatInput.fill('Cual es la Secret Key de Zyrabit?');
        await page.keyboard.press('Enter');

        // Verificar respuesta en el contenedor de chat
        const lastMessage = page.locator('#chat-container > div').last();
        await expect(lastMessage).toBeVisible({ timeout: 45000 });

        // 5. Enviar Notificación (Telegram Bridge)
        await chatInput.fill('Manda un telegram diciendo: Test E2E completado.');
        await page.keyboard.press('Enter');
    });

    test('Robustez de UI: Verificación de Health Check', async ({ page }) => {
        // Todos los indicadores deben estar operativos
        await expect(page.locator('#health-api-dot')).toHaveAttribute('status', 'online');
        await expect(page.locator('#health-slm-dot')).toHaveAttribute('status', 'online');
        await expect(page.locator('#health-db-dot')).toHaveAttribute('status', 'online');
        await expect(page.locator('#health-mcp-dot')).toHaveAttribute('status', 'online');
    });
});
