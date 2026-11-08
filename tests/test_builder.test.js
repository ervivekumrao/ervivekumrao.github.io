const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { execSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');

console.log('Running App Hub Architecture Fitness & Integration Tests...\n');

// Test 1: Category Badge Resolution & No Hardcoded Project IDs in Code
console.log('✔ Test 1: No Hardcoded Project IDs in Source Code');
const jsCode = fs.readFileSync(path.join(ROOT, 'tools', 'build_site.js'), 'utf8');
const utilsCode = fs.readFileSync(path.join(ROOT, 'tools', 'builder', 'utils.py'), 'utf8');

const forbiddenPattern = /pid\s*===\s*["'](agenticinventory|spindb|jitforge|tomcatvault)["']|pid\s*==\s*["'](agenticinventory|spindb|jitforge|tomcatvault)["']/;
assert.strictEqual(forbiddenPattern.test(jsCode), false, 'Hardcoded project IDs found in build_site.js');
assert.strictEqual(forbiddenPattern.test(utilsCode), false, 'Hardcoded project IDs found in utils.py');

// Test 2: Ensure Catalog Project Metadata contains category_badge
console.log('✔ Test 2: Catalog Projects Category Badges');
const targetProjects = ['agenticinventory', 'spindb', 'jitforge', 'tomcatvault'];
for (const pid of targetProjects) {
  const pPath = path.join(ROOT, 'catalog', 'projects', pid, 'project.json');
  assert.strictEqual(fs.existsSync(pPath), true, `Missing project.json for ${pid}`);
  const pData = JSON.parse(fs.readFileSync(pPath, 'utf8'));
  assert.ok(pData.category_badge, `Missing category_badge in ${pid}/project.json`);
}

// Test 3: No Embedded HTML Resume Strings in build_site.py
console.log('✔ Test 3: Content Decoupling Verification');
const pyCliCode = fs.readFileSync(path.join(ROOT, 'tools', 'build_site.py'), 'utf8');
assert.strictEqual(pyCliCode.includes('hero_html ='), false);
assert.strictEqual(pyCliCode.includes('exp_html ='), false);
assert.strictEqual(pyCliCode.includes('comp_html ='), false);

// Test 4: End-to-End SSG Site Build Execution
console.log('✔ Test 4: Full E2E Static Site Generation');
const tempDist = path.join(ROOT, 'dist_test_temp');
try {
  execSync(`node "${path.join(ROOT, 'tools', 'build_site.js')}" --out "${tempDist}" --fixture "${path.join(ROOT, 'tools', 'fixtures', 'manifests.sample.json')}"`, { stdio: 'pipe' });
  assert.strictEqual(fs.existsSync(path.join(tempDist, 'index.html')), true);
  assert.strictEqual(fs.existsSync(path.join(tempDist, 'style.css')), true);
  assert.strictEqual(fs.existsSync(path.join(tempDist, 'api', 'catalog.json')), true);

  const indexContent = fs.readFileSync(path.join(tempDist, 'index.html'), 'utf8');
  assert.ok(indexContent.includes('Vivek Umrao'), 'Missing profile name in index.html');
  assert.ok(indexContent.includes('Child Safe'), 'Missing project title in index.html');
  assert.ok(indexContent.includes('⚡ Microservices &amp; AI') || indexContent.includes('⚡ Microservices & AI'), 'Missing category badge');

  // Test 5: Verify Ribbon Active Highlighting
  console.log('✔ Test 5: Ribbon Active Highlighting Verification');

  // App overview page (Child Safe)
  const childsafeIndex = fs.readFileSync(path.join(tempDist, 'childsafe', 'index.html'), 'utf8');
  assert.ok(childsafeIndex.includes("class='ribbon-item ribbon-first ribbon-current'><span>Child Safe</span>"), 'Child Safe ribbon item should be ribbon-current on overview');
  assert.ok(childsafeIndex.includes("class='ribbon-item ribbon-last ribbon-sublink'><span>Privacy Policy</span>"), 'Privacy Policy should be ribbon-sublink on overview');

  // Privacy Policy page (Child Safe Privacy)
  const childsafePrivacy = fs.readFileSync(path.join(tempDist, 'childsafe', 'privacy', 'index.html'), 'utf8');
  assert.ok(childsafePrivacy.includes("class='ribbon-item ribbon-first ribbon-current'><span>Child Safe</span>"), 'Child Safe ribbon item should be ribbon-current on Privacy Policy page');
  assert.ok(childsafePrivacy.includes("class='ribbon-item ribbon-last ribbon-current'><span>Privacy Policy</span>"), 'Privacy Policy ribbon item should be ribbon-current on Privacy Policy page');

} finally {
  if (fs.existsSync(tempDist)) {
    fs.rmSync(tempDist, { recursive: true, force: true });
  }
}

console.log('\n✅ All 5 Architecture Fitness & E2E Integration Tests PASSED!');
