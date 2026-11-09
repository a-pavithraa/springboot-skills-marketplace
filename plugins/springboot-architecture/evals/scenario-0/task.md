# Product Catalogue Service Setup

## Problem/Feature Description

The engineering team at Plenish Commerce is extracting their product catalogue into its own service. Today it lives inside a monolith alongside checkout, inventory and accounts, and does basic create, read, update and delete work for products and categories, with simple filtering and listing. The team is five developers, and they expect the service to run as it is for the next year or two.

There is no project yet. The team lead wants a new Spring Boot service set up the way the team sets up new services, using PostgreSQL and Maven, and a short written recommendation the rest of the team can review before more code is written.

## Output Specification

Produce in your working directory:

1. **`scaffold-recommendation.md`**: the recommended structure and why, how the project was generated and with which versions and dependencies, what was applied from the team's templates, and the next steps.

2. **`product-catalogue/`**: the project, with at least a `pom.xml`, a controller and a repository for products, and a database migration that creates the products table.

Leave no placeholder or unfinished value in the project files.
