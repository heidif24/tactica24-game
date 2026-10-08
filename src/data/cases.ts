import type { Case } from '../types';
import { CASE_det_01 } from './cases/det_01';
import { CASE_det_02 } from './cases/det_02';
import { CASE_crm_01 } from './cases/crm_01';
import { CASE_pol_01 } from './cases/pol_01';
import { CASE_mil_01 } from './cases/mil_01';
import { CASE_plu_01 } from './cases/plu_01';
import { CASE_hak_01 } from './cases/hak_01';
import { CASE_doc_01 } from './cases/doc_01';

export const CASES: Case[] = [
  CASE_det_01,
  CASE_det_02,
  CASE_crm_01,
  CASE_pol_01,
  CASE_mil_01,
  CASE_plu_01,
  CASE_hak_01,
  CASE_doc_01,
];

export function getCasesForRole(roleId: string) {
  return CASES.filter((c) => c.roleId === roleId);
}

export function getCaseById(id: string) {
  return CASES.find((c) => c.id === id);
}
