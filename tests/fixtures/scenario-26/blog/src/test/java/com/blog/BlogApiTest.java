package com.blog;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.support.TransactionTemplate;
import java.time.Instant;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
@SpringBootTest @AutoConfigureMockMvc
class BlogApiTest {
  @Autowired MockMvc mvc; @Autowired PostRepository posts; @Autowired TagRepository tags; @Autowired TransactionTemplate tx;

  @Test void feedShowsCommentsAndTags() throws Exception {
    Long id = tx.execute(s -> {
      Tag java = tags.save(new Tag("java-" + System.nanoTime()));
      Post post = new Post("Hello", Instant.now());
      post.addComment("Nice"); post.addTag(java);
      return posts.save(post).getId();
    });
    mvc.perform(get("/api/posts")).andExpect(status().isOk())
        .andExpect(jsonPath("$[?(@.id == " + id + ")].comments[0]").value("Nice"));
  }
}
