package com.blog;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;
@Service
public class PostService {
  public record PostView(Long id, String title, List<String> comments, List<String> tags) {}
  private final PostRepository posts;
  public PostService(PostRepository posts) { this.posts = posts; }

  /** The home page feed: every post, newest first, with all its comments and tags. The blog has about 50 posts. */
  @Transactional(readOnly = true)
  public List<PostView> feed() {
    return posts.findAllByOrderByPublishedAtDesc().stream()
        .map(p -> new PostView(p.getId(), p.getTitle(),
            p.getComments().stream().map(Comment::getText).toList(),
            p.getTags().stream().map(Tag::getName).toList()))
        .toList();
  }

  /** Takes one tag off a post. Editors do this often. */
  @Transactional
  public void removeTag(Long postId, Long tagId) {
    posts.findById(postId).orElseThrow().removeTag(tagId);
  }

  /** Deletes a post and its comments. Its tags stay, because other posts use them. */
  @Transactional
  public void delete(Long postId) {
    posts.deleteById(postId);
  }
}
