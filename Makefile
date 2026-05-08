.PHONY: api-schema fe-types dev-setup

# Экспорт OpenAPI схемы (backend)
api-schema:
	python manage.py spectacular --skip-checks --validate --file api-schema.yaml
	@echo "✅ api-schema.yaml created"

# Генерация TypeScript типов из схемы (frontend)
fe-types: api-schema
	cd frontend && pnpm run generate:api-types
	@echo "✅ src/shared/api/schema.d.ts created"

dev-setup:
	pip install -r requirements.lock
	pip install -e ".[dev,test]"
	cd frontend && pnpm install
	@echo "✅ Ready"
