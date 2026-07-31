# Data Layer

The current v4.3 test package includes the portable PostgreSQL database package under `data-layer/database`.

It remains logically separate from the public static UI and the existing backend code. The first containerized deployment can run the UI, backend, and data layer on the same task/host while preserving boundaries for later AWS, Azure, or other cloud separation.
