import { expect, test } from '@playwright/test';
import type { Evaluation, EvidencePage, InvestigationResponse, JobDetail } from '../src/api/contracts.generated';

for (const viewport of [{ width: 1280, height: 900 }]) {
  test(`real decision path ${viewport.width}x${viewport.height}`, async ({ page }, testInfo) => {
    await page.setViewportSize(viewport);
    const hosts = new Set<string>();
    page.on('request', request => { if (request.url().startsWith('http')) hosts.add(new URL(request.url()).hostname); });
    const first = page.waitForResponse(response => response.url().endsWith('/evaluate'));
    const auditResponse = page.waitForResponse(response => response.url().includes('/investigations/'));
    await page.goto('/');
    const initial = await (await first).json() as Evaluation;
    expect(initial.meta.data_origin).toBe('official_dataset');
    for (const title of ['Where the money goes', 'Where to cut', 'If this decision is wrong']) await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible();
    await expect(page.locator('.scope-pill')).toContainText('Marginal scope');
    const evidenceResponse = page.waitForResponse(response => response.url().includes('/cpu_migration/evidence'));
    await page.getByTestId('evidence-cpu_migration').click();
    const evidence = await (await evidenceResponse).json() as EvidencePage;
    expect(evidence.meta.evaluation_id).toBe(initial.meta.evaluation_id);
    expect(evidence.scope).toBe('marginal');
    const dialog = page.getByRole('dialog');
    if (viewport.width > 760) await page.mouse.click(8, 8);
    await page.keyboard.press('Shift+Tab');
    expect(await dialog.evaluate(element => element.contains(document.activeElement))).toBe(true);
    await expect(page.locator('.page-intro')).toHaveAttribute('inert', '');
    const candidate = evidence.rows.find(row => row.eligibility === 'included' && row.finding_ids.length > 0);
    expect(candidate).toBeTruthy();
    await dialog.getByRole('button', { name: `View finding ${candidate!.finding_ids[0]}`, exact: true }).first().click();
    await expect(dialog.getByText('Reported impact', { exact: true })).toBeVisible();
    const jobResponse = page.waitForResponse(response => response.url().includes(`/jobs/${candidate!.job_id}?`));
    await dialog.getByRole('button', { name: `View job ${candidate!.job_id}`, exact: true }).click();
    const job = await (await jobResponse).json() as JobDetail;
    await expect(dialog.getByRole('table', { name: 'Physical GPU records' })).toBeVisible();
    await expect(dialog.locator('tbody tr')).toHaveCount(job.gpus.length);
    await page.screenshot({ path: `../../out/ui/evidence-${viewport.width}.png` });
    await dialog.getByRole('button', { name: 'Back to finding', exact: true }).click();
    await expect(dialog.getByText('Reported impact', { exact: true })).toBeVisible();
    await dialog.getByRole('button', { name: /Back to evidence/ }).click();
    await page.keyboard.press('Escape');
    await expect(page.getByTestId('evidence-cpu_migration')).toBeFocused();
    const idle = initial.actions.find(action => action.action_id === 'idle_session_reclaim')!;
    await page.locator('.action-ranking').getByRole('button', { name: idle.title, exact: true }).click();
    await expect(page.locator('.scope-pill')).toContainText('Standalone scope');
    const standaloneResponse = page.waitForResponse(response => response.url().includes('/idle_session_reclaim/evidence'));
    await page.getByTestId('evidence-idle_session_reclaim').click();
    expect((await (await standaloneResponse).json()).scope).toBe('standalone');
    await page.keyboard.press('Escape');
    await page.locator('.checks').getByRole('button', { name: idle.title, exact: true }).click();
    await page.getByLabel('GPU reference price', { exact: true }).fill(String(initial.request.pricing.usd_per_gpu_hour + 1));
    await expect(page.getByText('Unapplied changes')).toBeVisible();
    await expect(page.locator('.scope-pill')).toContainText('Standalone scope');
    const updatedResponse = page.waitForResponse(response => response.url().endsWith('/evaluate'));
    await page.getByRole('button', { name: 'Apply scenario' }).click();
    const updated = await (await updatedResponse).json() as Evaluation;
    expect(updated.meta.evaluation_id).not.toBe(initial.meta.evaluation_id);
    for (const card of await page.locator('.decision-cards > article').all()) await expect(card).toHaveAttribute('data-evaluation-id', updated.meta.evaluation_id!);
    await expect(page.locator('.scope-pill')).toContainText('Marginal scope');
    const updatedIdle = updated.actions.find(action => action.action_id === 'idle_session_reclaim')!;
    expect(updated.portfolio.overlap_jobs).toBeGreaterThan(0);
    expect(updatedIdle.marginal_recoverable_gpu_hours!.point).toBeLessThan(updatedIdle.standalone_recoverable_gpu_hours.point);
    const number = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 });
    for (const [label, value] of [
      ['Standalone recoverable capacity', updatedIdle.standalone_recoverable_gpu_hours.point],
      ['Marginal recoverable capacity', updatedIdle.marginal_recoverable_gpu_hours!.point],
      ['Portfolio recoverable GPU-hours', updated.portfolio.recoverable_gpu_hours.point],
    ] as const) await expect(page.locator('.metric').filter({ has: page.getByText(label, { exact: true }) }).locator('strong')).toContainText(number.format(value));
    await expect(page.locator('.portfolio > p')).toContainText(`${updated.portfolio.overlap_jobs} overlap jobs`);
    const marginalResponse = page.waitForResponse(response => response.url().includes('/idle_session_reclaim/evidence'));
    await page.getByTestId('evidence-idle_session_reclaim').click();
    const marginal = await (await marginalResponse).json() as EvidencePage;
    expect(marginal.meta.evaluation_id).toBe(updated.meta.evaluation_id);
    expect(marginal.scope).toBe('marginal');
    await expect(dialog.getByText(/marginal scope/)).toBeVisible();
    const overlapRows = marginal.rows.filter(row => row.eligibility === 'overlap_assigned_elsewhere');
    expect(overlapRows.length).toBeGreaterThan(0);
    const overlap = dialog.locator('[data-eligibility="overlap_assigned_elsewhere"]').filter({ hasText: `Job ${overlapRows[0].job_id}` });
    await expect(overlap).toBeVisible();
    await expect(overlap).toContainText('OVERLAP_ASSIGNED_TO_CPU_MIGRATION');
    await page.keyboard.press('Escape');
    const audit = await (await auditResponse).json() as InvestigationResponse;
    expect(['partial', 'completed']).toContain(audit.investigation.status);
    const requiredTools = ['tools/list', 'health', 'list_rules', 'recommendations', 'underperforming', 'list_findings', 'causal', 'neighbor'];
    const successfulTools = new Set(audit.investigation.tool_calls.filter(call => call.status === 'success').map(call => call.tool_name));
    for (const tool of requiredTools) expect(successfulTools.has(tool), `successful ${tool} call`).toBe(true);
    await page.getByText('MCP investigation record', { exact: true }).click();
    await expect(page.getByText(/Nominal capacity at stake over 24 hours:/)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Refresh investigation' })).toBeVisible();
    for (const tool of requiredTools) await expect(page.locator('.audit .tool-call summary').filter({ hasText: `${tool} — success` }).first()).toBeVisible();
    if (audit.investigation.status === 'partial') {
      expect(audit.investigation.limitations.length).toBeGreaterThan(0);
      for (const limitation of audit.investigation.limitations) await expect(page.locator('.audit').getByText(limitation, { exact: true })).toBeVisible();
      const truncated = audit.investigation.nodes.filter(node => node.truncated);
      expect(truncated.length).toBeGreaterThan(0);
      for (const node of truncated) {
        const article = page.locator('.audit article').filter({ hasText: node.node_name });
        await expect(article).toContainText('Truncated evidence — investigation is incomplete');
        await expect(article).toContainText(`${node.returned_findings} returned / ${node.reported_findings} reported findings`);
      }
    }
    const firstCall = page.locator('.audit .tool-call').first();
    await firstCall.locator('summary').click();
    await expect(firstCall.locator('pre')).toBeVisible();
    page.once('dialog', prompt => prompt.accept('UI acceptance test'));
    const claimsResponse = page.waitForResponse(response => response.url().endsWith('/claims'));
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download claims' }).click();
    const claims = await claimsResponse;
    expect(claims.request().postDataJSON().evaluation_request).toEqual(updated.request);
    expect((await claims.json()).claims.analysis_provenance.evaluation_id).toBe(updated.meta.evaluation_id);
    expect((await downloadPromise).suggestedFilename()).toBe('claims.json');
    await page.screenshot({ path: `../../out/ui/dashboard-${viewport.width}.png`, fullPage: true });
    await testInfo.attach('network-hosts', { body: JSON.stringify([...hosts]), contentType: 'application/json' });
    expect([...hosts].every(host => ['localhost', '127.0.0.1'].includes(host))).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}
