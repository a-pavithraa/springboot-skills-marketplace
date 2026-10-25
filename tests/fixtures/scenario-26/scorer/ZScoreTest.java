package com.blog;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.config.BeanPostProcessor;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;
import javax.sql.DataSource;
import java.lang.reflect.*;
import java.sql.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;

/** Hidden scorer: 50 posts x 20 comments x 10 shared tags. Counts JDBC statements and rows read per request. */
@SpringBootTest @AutoConfigureMockMvc
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class ZScoreTest {
  static final AtomicInteger STATEMENTS = new AtomicInteger(), ROWS = new AtomicInteger();

  @TestConfiguration static class Counting {
    @Bean static BeanPostProcessor countingDataSource() {
      return new BeanPostProcessor() {
        @Override public Object postProcessAfterInitialization(Object bean, String name) {
          if (!(bean instanceof DataSource ds)) return bean;
          return proxy(DataSource.class, ds, (m, r) -> r instanceof Connection c ? proxy(Connection.class, c, (m2, r2) -> {
            if (r2 instanceof Statement s && m2.getName().matches("prepareStatement|prepareCall|createStatement")) {
              STATEMENTS.incrementAndGet();
              Class<?> type = s instanceof CallableStatement ? CallableStatement.class
                  : s instanceof PreparedStatement ? PreparedStatement.class : Statement.class;
              return proxy(type, s, (m3, r3) -> r3 instanceof ResultSet rs ? proxy(ResultSet.class, rs, (m4, r4) -> {
                if (m4.getName().equals("next") && Boolean.TRUE.equals(r4)) ROWS.incrementAndGet();
                return r4;
              }) : r3);
            }
            return r2;
          }) : r);
        }
      };
    }
    interface After { Object apply(Method m, Object result); }
    static Object proxy(Class<?> type, Object target, After after) {
      return Proxy.newProxyInstance(type.getClassLoader(), new Class<?>[]{type}, (p, m, a) -> {
        try { return after.apply(m, m.invoke(target, a)); } catch (InvocationTargetException e) { throw e.getCause(); }
      });
    }
  }

  @Autowired MockMvc mvc; @Autowired JdbcTemplate jdbc;
  static final Map<String, String> SCORE = new LinkedHashMap<>();

  @BeforeEach void seed() {
    jdbc.update("delete from post_tags"); jdbc.update("delete from comments");
    jdbc.update("delete from posts"); jdbc.update("delete from tags");
    List<Object[]> t = new ArrayList<>(), p = new ArrayList<>(), c = new ArrayList<>(), pt = new ArrayList<>();
    for (int i = 1; i <= 10; i++) t.add(new Object[]{i, "tag-" + i});
    long comment = 1;
    for (int i = 1; i <= 50; i++) {
      p.add(new Object[]{1000 + i, "Post " + i, new Timestamp(1_700_000_000_000L + i * 60_000L)});
      for (int k = 1; k <= 20; k++) c.add(new Object[]{comment++, 1000 + i, "Comment " + k + " on post " + i});
      for (int k = 1; k <= 10; k++) pt.add(new Object[]{1000 + i, k});
    }
    jdbc.batchUpdate("insert into tags(id, name) values (?, ?)", t);
    jdbc.batchUpdate("insert into posts(id, title, published_at) values (?, ?, ?)", p);
    jdbc.batchUpdate("insert into comments(id, post_id, text) values (?, ?, ?)", c);
    jdbc.batchUpdate("insert into post_tags(post_id, tag_id) values (?, ?)", pt);
  }

  int status(org.springframework.test.web.servlet.RequestBuilder rb, StringBuilder body) throws Exception {
    STATEMENTS.set(0); ROWS.set(0);
    try {
      var res = mvc.perform(rb).andReturn().getResponse();
      if (body != null) body.append(res.getContentAsString());
      return res.getStatus();
    } catch (jakarta.servlet.ServletException e) {
      System.out.println("SCORE| exception = " + e.getRootCause());
      return 500;
    }
  }

  int count(String sql) { return jdbc.queryForObject(sql, Integer.class); }

  @Test @Order(1) void feed() throws Exception {
    StringBuilder b = new StringBuilder();
    int status = status(get("/api/posts"), b);
    SCORE.put("P6 feed status/statements/rows read", status + "/" + STATEMENTS.get() + "/" + ROWS.get());
    if (status != 200) return;
    Object doc = JsonPath.read(b.toString(), "$");
    List<?> items = doc instanceof List<?> li ? li : (List<?>) JsonPath.read(b.toString(), "$.content");
    Map<?, ?> newest = (Map<?, ?>) items.get(0);
    SCORE.put("feed correct (50 posts, newest has 20 comments and 10 tags)", "" + (items.size() == 50
        && ((List<?>) newest.get("comments")).size() == 20 && ((List<?>) newest.get("tags")).size() == 10));
  }

  @Test @Order(2) void removeTag() throws Exception {
    int status = status(delete("/api/posts/1001/tags/5"), null);
    SCORE.put("P5 remove tag status/statements", status + "/" + STATEMENTS.get());
    SCORE.put("remove tag correct (9 left, tag kept)", "" + (count("select count(*) from post_tags where post_id = 1001") == 9
        && count("select count(*) from tags where id = 5") == 1));
  }

  @Test @Order(3) void deletePost() throws Exception {
    int status = status(delete("/api/posts/1002"), null);
    SCORE.put("P7 delete post: status/post gone/comments gone/shared tags kept", status
        + "/" + (count("select count(*) from posts where id = 1002") == 0)
        + "/" + (count("select count(*) from comments where post_id = 1002") == 0)
        + "/" + (count("select count(*) from tags") == 10 && count("select count(*) from post_tags where post_id = 1003") == 10));
  }

  @AfterAll static void print() { SCORE.forEach((k, v) -> System.out.println("SCORE| " + k + " = " + v)); }
}
