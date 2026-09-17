import contract from '../../../contracts/decision.schema.json';

type Schema = {
  $ref?: string;
  anyOf?: Schema[];
  type?: string;
  enum?: unknown[];
  const?: unknown;
  required?: string[];
  properties?: Record<string, Schema>;
  additionalProperties?: boolean | Schema;
  items?: Schema;
  ge?: number;
  le?: number;
};
export type ResponseContract = 'DecisionConfig' | 'Evaluation' | 'EvidencePage' | 'JobDetail' | 'FindingDetail' | 'InvestigationResponse' | 'ClaimsResponse';
const definitions = contract.$defs as Record<string, Schema>;

// The frozen shared schema uses refs, unions, primitive types, object fields,
// arrays and literal values. Validate that exact vocabulary at the HTTP boundary.
function matches(value: unknown, schema: Schema): boolean {
  if (typeof value === 'number' && (!Number.isFinite(value) || (schema.ge !== undefined && value < schema.ge) || (schema.le !== undefined && value > schema.le))) return false;
  if (schema.$ref) {
    const definition = definitions[schema.$ref.replace('#/$defs/', '')];
    return !!definition && matches(value, definition);
  }
  if (schema.anyOf && !schema.anyOf.some(option => matches(value, option))) return false;
  if (schema.enum && !schema.enum.includes(value)) return false;
  if ('const' in schema && value !== schema.const) return false;
  if (schema.type === 'null') return value === null;
  if (schema.type === 'string') return typeof value === 'string';
  if (schema.type === 'boolean') return typeof value === 'boolean';
  if (schema.type === 'number' || schema.type === 'integer') {
    return typeof value === 'number' && Number.isFinite(value) && (schema.type !== 'integer' || Number.isInteger(value)) &&
      (schema.ge === undefined || value >= schema.ge) && (schema.le === undefined || value <= schema.le);
  }
  if (schema.type === 'array') return Array.isArray(value) && (!schema.items || value.every(item => matches(item, schema.items!)));
  if (schema.type === 'object') {
    if (value === null || typeof value !== 'object' || Array.isArray(value)) return false;
    const object = value as Record<string, unknown>;
    if (schema.required?.some(key => !Object.prototype.hasOwnProperty.call(object, key))) return false;
    return Object.entries(object).every(([key, item]) => {
      const property = schema.properties?.[key];
      if (property) return matches(item, property);
      if (schema.additionalProperties === false) return false;
      return typeof schema.additionalProperties !== 'object' || matches(item, schema.additionalProperties);
    });
  }
  return true;
}

export function validResponse(name: ResponseContract, value: unknown): boolean {
  return matches(value, definitions[name]);
}
