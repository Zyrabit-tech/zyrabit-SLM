import { test, expect } from '@playwright/test';

const baseURL = process.env.ZYRABIT_E2E_URL || 'http://localhost:8080';
const fixturePath = process.env.ZYRABIT_E2E_FIXTURE
    || '/workspace/zyrabit-slm/api-rag/docs/zyrabit-cioreview-en.pdf';

test.describe('Document workspace', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto(baseURL);
        await expect(page.getByRole('heading', { name: 'Think with your documents.' })).toBeVisible();
        await expect(page.getByRole('button', { name: /Import documents/i })).toBeVisible();
    });

    test('shows the document-first workspace and opens the file chooser', async ({ page }) => {
        const fileChooser = page.waitForEvent('filechooser');
        await page.getByRole('button', { name: /Import documents/i }).click();
        await (await fileChooser).setFiles(fixturePath);

        await expect(page.getByText('zyrabit-cioreview-en.pdf')).toBeVisible({ timeout: 30_000 });
    });

    test('prefills a contextual question from an empty-state action', async ({ page }) => {
        await page.getByRole('button', { name: /Summarize a document/i }).click();
        await expect(page.locator('#chat-input')).toHaveValue('Give me a concise summary of the key points.');
    });

    test('renders health indicators without exposing infrastructure as primary UI', async ({ page }) => {
        await expect(page.locator('#health-api-dot')).toHaveAttribute('status', 'online');
        await expect(page.locator('#health-db-dot')).toHaveAttribute('status', 'online');
        await expect(page.locator('#health-slm-dot')).toHaveAttribute('status', 'online');
    });
});
