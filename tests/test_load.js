const { createJiti } = require('jiti');
const jiti = createJiti(__filename);
try {
  jiti('/root/t1d/.pi/extensions/clanker-ops/index.ts');
  console.log('✅ Extension module loaded successfully');
} catch (e) {
  console.error('❌ Loading failed:', e);
}
