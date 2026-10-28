import {test} from 'node:test';
import assert from 'node:assert/strict';
import {csvCell,findingsCsv} from '../src/export.js';
test('CSV cells neutralize formulas and quote delimiters',()=>{
  for (const value of ['=1+1','+SUM(A1)','-1','@SUM(A1)','  =1','\tformula']) assert.equal(csvCell(value), '"\''+value+'"');
  assert.equal(csvCell('a,"b"'), '"a,""b"""');
  assert.equal(csvCell('line\nnext'), '"line\nnext"');
  assert.equal(csvCell(null), '"null"');
});
test('Findings export preserves provenance, recommendations, and empty headers',()=>{
  const report={analysis_version:'1.1.0',synthetic:true,config:{recurring_min:3},findings:[{finding_id:'F001',title:'=HYPERLINK("x")',affected_routes:['r'],observed_period:{start:'2026-01-01'},source_record_references:[1,3],recommendations:['Inspect logs'],evidence:{classification_methods:['code_rule']},limitations:['Not causal']}]};
  const csv=findingsCsv(report);
  assert.ok(csv.includes('"source_record_references"'));
  assert.ok(csv.includes('"[1,3]"'));
  assert.ok(csv.includes('code_rule')&&csv.includes('Inspect logs')&&csv.includes('Not causal'));
  assert.ok(csv.includes('"\'=HYPERLINK'));
  assert.equal(findingsCsv({...report,findings:[]}).split('\r\n').length,1);
  assert.deepEqual(JSON.parse(JSON.stringify(report)),report);
});
