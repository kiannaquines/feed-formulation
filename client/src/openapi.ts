export type ApiSchema = {
  $ref?: string;
  type?: string;
  title?: string;
  description?: string;
  format?: string;
  example?: unknown;
  default?: unknown;
  enum?: unknown[];
  properties?: Record<string, ApiSchema>;
  required?: string[];
  items?: ApiSchema;
  additionalProperties?: ApiSchema | boolean;
  anyOf?: ApiSchema[];
  allOf?: ApiSchema[];
};

export type ApiParameter = {
  name: string;
  in: 'path' | 'query' | 'header' | 'cookie';
  required?: boolean;
  description?: string;
  schema?: ApiSchema;
};

export type ApiOperation = {
  key: string;
  method: string;
  path: string;
  tag: string;
  summary: string;
  description: string;
  deprecated: boolean;
  parameters: ApiParameter[];
  requestSchema?: ApiSchema;
  secured: boolean;
};

type RawOperation = {
  tags?: string[];
  summary?: string;
  description?: string;
  deprecated?: boolean;
  parameters?: ApiParameter[];
  requestBody?: {
    content?: Record<string, { schema?: ApiSchema }>;
  };
  security?: unknown[];
};

export type OpenApiDocument = {
  info: { title: string; version: string };
  tags?: { name: string; description?: string }[];
  paths: Record<string, Record<string, RawOperation>>;
  components?: { schemas?: Record<string, ApiSchema> };
};

const methods = ['get', 'post', 'put', 'patch', 'delete'];

export function getOperations(document: OpenApiDocument): ApiOperation[] {
  const operations = Object.entries(document.paths).flatMap(([path, pathOperations]) =>
    Object.entries(pathOperations)
      .filter(([method]) => methods.includes(method))
      .map(([method, operation]) => ({
        key: `${method.toUpperCase()} ${path}`,
        method: method.toUpperCase(),
        path,
        tag: operation.tags?.[0] || 'Other',
        summary: operation.summary || path,
        description: operation.description || '',
        deprecated: Boolean(operation.deprecated),
        parameters: operation.parameters || [],
        requestSchema: operation.requestBody?.content?.['application/json']?.schema,
        secured: Boolean(operation.security?.length),
      })),
  );
  const legacy = operations.filter((operation) =>
    operation.path.includes('/nutrient-requirements/') &&
    ['PUT', 'DELETE'].includes(operation.method),
  ).map((operation) => ({
    ...operation,
    key: `${operation.method} ${operation.path.replace('nutrient-requirements', 'nutrient-requrments')}`,
    path: operation.path.replace('nutrient-requirements', 'nutrient-requrments'),
    summary: `${operation.summary} (legacy URL)`,
    deprecated: true,
  }));
  return [...operations, ...legacy];
}

export function resolveSchema(
  schema: ApiSchema,
  schemas: Record<string, ApiSchema>,
): ApiSchema {
  if (schema.$ref) {
    const name = schema.$ref.split('/').at(-1) || '';
    return schemas[name] ? resolveSchema(schemas[name], schemas) : schema;
  }
  return schema;
}

function schemaValue(
  rawSchema: ApiSchema,
  schemas: Record<string, ApiSchema>,
  depth = 0,
): unknown {
  if (depth > 5) return null;
  const schema = resolveSchema(rawSchema, schemas);
  if (schema.example !== undefined) return schema.example;
  if (schema.default !== undefined) return schema.default;
  if (schema.enum?.length) return schema.enum[0];
  if (schema.anyOf?.length) {
    const choice = schema.anyOf.find((item) => item.type !== 'null');
    return choice ? schemaValue(choice, schemas, depth + 1) : null;
  }
  if (schema.allOf?.length) {
    return Object.assign(
      {},
      ...schema.allOf.map((item) => schemaValue(item, schemas, depth + 1)),
    );
  }
  if (schema.type === 'array') {
    return schema.items ? [schemaValue(schema.items, schemas, depth + 1)] : [];
  }
  if (schema.type === 'object' || schema.properties) {
    if (!schema.properties && schema.additionalProperties) {
      return {
        nutrient_name: typeof schema.additionalProperties === 'object'
          ? schemaValue(schema.additionalProperties, schemas, depth + 1)
          : 0,
      };
    }
    return Object.fromEntries(
      Object.entries(schema.properties || {})
        .filter(([name, property]) => schema.required?.includes(name) || property.default !== undefined)
        .map(([name, property]) => [name, schemaValue(property, schemas, depth + 1)]),
    );
  }
  if (schema.type === 'boolean') return false;
  if (schema.type === 'integer' || schema.type === 'number') return 0;
  if (schema.format === 'email') return 'name@example.com';
  if (schema.format === 'uuid') return crypto.randomUUID();
  if (schema.format === 'date-time') return new Date().toISOString();
  return '';
}

export function bodyExample(
  operation: ApiOperation,
  schemas: Record<string, ApiSchema>,
): string {
  if (operation.path === '/v4/feed/formulate') {
    return JSON.stringify({
      ingredients: [
        { name: 'Corn', cost_per_kg: 2, nutrients: { protein_percent: 8 } },
        { name: 'Soybean meal', cost_per_kg: 4, nutrients: { protein_percent: 44 } },
      ],
      nutrient_requirements: { protein_percent: 17 },
    }, null, 2);
  }
  if (operation.path.startsWith('/v4/ingredients/') && operation.requestSchema) {
    return JSON.stringify({
      name: 'New ingredient', price: 2,
      composition: { protein_percent: 8 }, is_available: true,
    }, null, 2);
  }
  return JSON.stringify(
    operation.requestSchema ? schemaValue(operation.requestSchema, schemas) : {},
    null,
    2,
  );
}
