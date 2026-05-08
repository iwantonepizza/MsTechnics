import { expect, test } from '@playwright/test'

test('login page renders', async ({ page }) => {
  await page.goto('/login')

  await expect(page.locator('input[name="username"]')).toBeVisible()
  await expect(page.locator('input[name="password"]')).toBeVisible()
})

test('requires auth before menu', async ({ page }) => {
  await page.goto('/menu')

  await expect(page).toHaveURL(/\/login/)
})
