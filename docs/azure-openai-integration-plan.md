# Future Azure OpenAI integration plan

Azure OpenAI is not integrated in this milestone. No endpoint, deployment, credential, or Azure SDK dependency has been added.

## Provider boundary

Define a future `TranslationAIProvider` interface whose input contains parsed CL, exact machine context, controlled retrieved examples, and an explicit output contract. Candidate implementations:

- `MockTranslationProvider` for deterministic development and tests;
- `AzureOpenAITranslationProvider` for organization-approved experiments.

Potential settings:

```text
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_DEPLOYMENT
AZURE_OPENAI_API_VERSION
```

Authentication should prefer managed identity or another enterprise-approved mechanism. Never hard-code credentials, place secrets in source control, or log prompts containing restricted source programs.

## Data boundaries

- internal approved data only;
- no public-web retrieval by default;
- explicit machine and immutable revision context;
- controlled example selection with eligibility filtering;
- restricted documents/programs excluded when required;
- provider, deployment, example IDs, data scope, and external-processing state audited;
- retention and regional processing governed by organizational approval.

Future UI disclosure:

```text
AI Provider: Azure OpenAI
Data Source: Internal Verified Translation Examples
Public Web: Disabled
```

## Future pipeline

```text
New Creo CL
  -> parse CL
  -> identify exact machine context
  -> retrieve verified historical pairs
  -> construct controlled AI context
  -> produce DRAFT translation
  -> parse G-code
  -> deterministic validation
  -> historical comparison
  -> toolpath visualization
  -> qualified review
```

AI output cannot bypass deterministic checks. Provider output is advisory, schema validated, and traceable to input segments and retrieved examples. Hidden model reasoning is not requested or exposed.

The initial experiment is retrieval-assisted/few-shot translation. Fine-tuning is deferred because retrieval is more auditable, easier to update and revoke, requires fewer examples, and keeps the evidence visible.
