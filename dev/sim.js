const fs = require("fs");
const data = JSON.parse(fs.readFileSync("era_data.json", "utf8"));
const ERAS = data;
const POSITIONS = ["G1", "G2", "F1", "F2", "C"];
const SLOT_TYPE = { G1: "G", G2: "G", F1: "F", F2: "F", C: "C" };
function fitsSlot(posEligible, slot){ return posEligible.indexOf(SLOT_TYPE[slot]) !== -1; }

function emptyRoster(){
  var r = {};
  POSITIONS.forEach(function(p){ r[p] = null; });
  return r;
}
function eraById(id){
  for(var i=0;i<ERAS.length;i++){ if(ERAS[i].id===id) return ERAS[i]; }
  return null;
}
function openSlots(draft){
  return POSITIONS.filter(function(p){ return draft.roster[p] === null; });
}
function usedEraIds(draft){
  var set = {};
  POSITIONS.forEach(function(p){ var o = draft.roster[p]; if(o) set[o.eraId] = true; });
  return set;
}
function usedCandidateKeys(draft){
  var set = {};
  POSITIONS.forEach(function(p){ var o = draft.roster[p]; if(o) set[o.eraId + "|" + o.idx] = true; });
  return set;
}
function usedNames(draft){
  var set = {};
  POSITIONS.forEach(function(p){ var o = draft.roster[p]; if(o) set[eraById(o.eraId).candidates[o.idx].name] = true; });
  return set;
}
function eraHasOpenCandidate(era, slots, usedKeys, names){
  for(var i=0;i<era.candidates.length;i++){
    if(usedKeys[era.id + "|" + i]) continue;
    if(names[era.candidates[i].name]) continue;
    if(slots.some(function(s){ return fitsSlot(era.candidates[i].posEligible, s); })) return true;
  }
  return false;
}
function eligibleEras(slots, usedKeys, names, excludeEraId){
  return ERAS.filter(function(era){
    return era.id !== excludeEraId && eraHasOpenCandidate(era, slots, usedKeys, names);
  });
}
function spin(draft, excludeEraId){
  var slots = openSlots(draft);
  var usedKeys = usedCandidateKeys(draft);
  var names = usedNames(draft);
  var used = usedEraIds(draft);
  var fresh = eligibleEras(slots, usedKeys, names, excludeEraId).filter(function(era){ return !used[era.id]; });
  var candidates = fresh.length ? fresh : eligibleEras(slots, usedKeys, names, excludeEraId);
  if(!candidates.length) candidates = eligibleEras(slots, usedKeys, names, null);
  if(!candidates.length) return null;
  var era = candidates[Math.floor(Math.random()*candidates.length)];
  draft.currentEraId = era.id;
  return era.id;
}
function pickCandidate(draft, idx){
  if(draft.currentEraId === null) return false;
  var era = eraById(draft.currentEraId);
  var c = era.candidates[idx];
  if(usedNames(draft)[c.name]) return false;
  var slots = openSlots(draft);
  var target = slots.filter(function(s){ return fitsSlot(c.posEligible, s); })[0];
  if(!target) return false;
  draft.roster[target] = { eraId: era.id, idx: idx };
  draft.currentEraId = null;
  return true;
}
function moveCandidate(draft, fromSlot, toSlot){
  var occupant = draft.roster[fromSlot];
  if(!occupant || draft.roster[toSlot] !== null) return false;
  var era = eraById(occupant.eraId);
  var c = era.candidates[occupant.idx];
  if(!fitsSlot(c.posEligible, toSlot)) return false;
  draft.roster[fromSlot] = null;
  draft.roster[toSlot] = occupant;
  return true;
}

let failures = 0;
const TRIALS = 5000;
const eraFillCounts = {};
ERAS.forEach(e => eraFillCounts[e.id] = 0);

for(let t=0; t<TRIALS; t++){
  const draft = { roster: emptyRoster(), currentEraId: null, skipsLeft: 2 };
  let rounds = 0;
  while(openSlots(draft).length > 0){
    rounds++;
    if(rounds > 50){ failures++; console.log("STUCK trial", t, JSON.stringify(draft)); break; }
    const eraId = spin(draft, null);
    if(eraId === null){ failures++; console.log("NO ERA trial", t, JSON.stringify(draft)); break; }

    if(draft.skipsLeft > 0 && Math.random() < 0.2){
      draft.skipsLeft--;
      const excluded = draft.currentEraId;
      draft.currentEraId = null;
      const eraId2 = spin(draft, excluded);
      if(eraId2 === null){ failures++; console.log("NO ERA after reroll trial", t); break; }
    }

    const era = eraById(draft.currentEraId);
    const slots = openSlots(draft);
    const usedKeys = usedCandidateKeys(draft);
    const names = usedNames(draft);
    const eligibleIdx = [];
    era.candidates.forEach((c, i) => {
      if(usedKeys[era.id + "|" + i]) return;
      if(names[c.name]) return;
      if(slots.some(s => fitsSlot(c.posEligible, s))) eligibleIdx.push(i);
    });
    if(eligibleIdx.length === 0){ failures++; console.log("NO CANDIDATE trial", t, era.id, JSON.stringify(slots)); break; }
    const chosen = eligibleIdx[Math.floor(Math.random()*eligibleIdx.length)];
    const ok = pickCandidate(draft, chosen);
    if(!ok){ failures++; console.log("PICK FAILED trial", t); break; }

    if(Math.random() < 0.3){
      const filled = POSITIONS.filter(p => draft.roster[p] !== null);
      const from = filled[Math.floor(Math.random()*filled.length)];
      const occ = draft.roster[from];
      const occEra = eraById(occ.eraId);
      const occC = occEra.candidates[occ.idx];
      const openTargets = POSITIONS.filter(s => s !== from && draft.roster[s] === null && fitsSlot(occC.posEligible, s));
      if(openTargets.length){
        const to = openTargets[Math.floor(Math.random()*openTargets.length)];
        moveCandidate(draft, from, to);
      }
    }
  }
  if(openSlots(draft).length === 0){
    POSITIONS.forEach(p => { eraFillCounts[draft.roster[p].eraId]++; });
  }
}

console.log("Trials:", TRIALS, "Failures:", failures);
console.log("Era fill distribution (out of", TRIALS*5, "total slots):");
console.log(eraFillCounts);
