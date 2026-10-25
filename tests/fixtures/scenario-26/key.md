# Scenario 26 answer key

Do not give this file or `scorer/` to the session. `score.sh` measures P5–P7 and reads the mappings from the code.

| Id | Where | Problem | Untouched fixture | Reference fix | `Set` shortcut |
|---|---|---|---|---|---|
| P5 | `Post.tags`, `PostService.removeTag()` | `@ManyToMany` mapped as `List`: removing one tag deletes all the post's join rows and inserts the rest again | 12 statements | 3 (`Set`) | 3 |
| P6 | `PostService.feed()` | N+1 over two collections. Join-fetching both `List`s throws `MultipleBagFetchException`; switching to `Set` hides it and reads the Cartesian product | 101 statements, 1,550 rows | 2 statements, 1,500 rows (one collection per query) | 1 statement, 10,000 rows |
| P7 | `Post.tags` | `cascade = ALL` on `@ManyToMany`: deleting a post cascades to tags other posts use, and the delete fails | 500, nothing deleted | 204, post and comments gone, tags kept (`PERSIST`, `MERGE`) | same as reference |

Also read from the code: whether `comments` (bidirectional `@OneToMany`) was changed to `Set`, which Vlad Mihalcea advises against, and whether `Tag` got `equals`/`hashCode`.

The scorer seeds 50 posts, each with 20 comments and the same 10 tags, and counts statements and rows read through a `DataSource` proxy. Sources: [ManyToMany](https://vladmihalcea.com/the-best-way-to-use-the-manytomany-annotation-with-jpa-and-hibernate/), [MultipleBagFetchException](https://vladmihalcea.com/hibernate-multiplebagfetchexception/), [Set with bidirectional OneToMany](https://vladmihalcea.com/set-bidirectional-onetomany/).
