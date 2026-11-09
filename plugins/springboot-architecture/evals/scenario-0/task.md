# Product Catalogue Service Setup

## Problem/Feature Description

The engineering team at Plenish Commerce has decided to extract their product catalogue into a dedicated microservice. The catalogue currently lives inside a monolithic codebase alongside checkout, inventory, and accounts — it handles basic CRUD operations for products and categories, with straightforward filtering and listing needs. The team is small (5 developers), and the new service is expected to be in active use for at least the next year or two before any significant architectural changes.

There's no existing project skeleton to start from. The team lead wants a solid foundation that follows the team's established Spring Boot 4 conventions: proper project structure, baseline dependencies, a scaffold recommendation document that can be reviewed by the rest of the team, and the core template files applied and filled in with the right package and domain names. The service should use a PostgreSQL database and Maven as the build tool.

## Output Specification

Produce the following in your working directory:

1. **`scaffold-recommendation.md`** — A project scaffold recommendation in the team's standard format, covering the recommended architecture pattern and reasoning, the project generator setup (generator choice, build tool, Java version, Spring Boot version, and core dependencies), which skill asset templates you would apply, and the next implementation steps.

2. **`product-catalogue/`** — A minimal project directory containing applied template files with all values filled in. At minimum, include:
   - A `pom.xml` with the correct Spring Boot version, Java version, and baseline dependencies
   - A sample controller file for the product domain (e.g., `ProductController.java`)
   - A sample repository file (e.g., `ProductRepository.java`)
   - A Flyway migration SQL file for a products table

3. **`check-report.md`** — A written report describing what `check_new_project.py` would validate and whether the generated project would pass each check, based on the files you've produced.

All template files must be production-ready — no stub or unfinished values should remain in the output files.
