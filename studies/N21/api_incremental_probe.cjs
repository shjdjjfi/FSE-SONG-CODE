// Narrow reproduction of the public Nest CLI #3312 failure mechanism.
// No Nest application is claimed. This calls the actual TypeScript API.
const fs = require('node:fs');
const path = require('node:path');
const ts = require(path.resolve(process.argv[2]));
const project = path.resolve(process.argv[3]);
const configFile = path.join(project, 'tsconfig.build.json');
const config = ts.readConfigFile(configFile, ts.sys.readFile);
if (config.error) throw new Error(ts.flattenDiagnosticMessageText(config.error.messageText, '\n'));
const parsed = ts.parseJsonConfigFileContent(config.config, ts.sys, project);
if (parsed.errors.length) throw new Error(parsed.errors.map(e => e.messageText).join('\n'));
const states = [];
function test(label, removeOutput, removeBuildinfo) {
  if (removeOutput) fs.rmSync(path.join(project, 'dist'), { recursive: true, force: true });
  if (removeBuildinfo) fs.rmSync(path.join(project, 'cache.tsbuildinfo'), { force: true });
  const program = ts.createIncrementalProgram({ rootNames: parsed.fileNames, options: parsed.options });
  const diagnostics = ts.getPreEmitDiagnostics(program.getProgram()).map(d => d.code);
  const result = program.emit();
  states.push({ label, removeOutput, removeBuildinfo,
    emitSkipped: result.emitSkipped, diagnosticCodes: diagnostics,
    jsExists: fs.existsSync(path.join(project,'dist','main.js')),
    buildinfoExists: fs.existsSync(path.join(project, 'cache.tsbuildinfo')) });
}
test('cold', false, false);
test('delete_dist_keep_info', true, false);
test('delete_dist_and_info', true, true);
process.stdout.write(JSON.stringify({ version: ts.version, states }));
