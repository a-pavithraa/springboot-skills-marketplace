package com.blog;
import jakarta.persistence.*; import java.time.Instant; import java.util.*;
@Entity @Table(name = "posts")
public class Post {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
  private String title;
  private Instant publishedAt;
  @OneToMany(mappedBy = "post", cascade = CascadeType.ALL, orphanRemoval = true)
  private List<Comment> comments = new ArrayList<>();
  @ManyToMany(cascade = CascadeType.ALL)
  @JoinTable(name = "post_tags", joinColumns = @JoinColumn(name = "post_id"), inverseJoinColumns = @JoinColumn(name = "tag_id"))
  private List<Tag> tags = new ArrayList<>();
  protected Post() {}
  public Post(String title, Instant publishedAt) { this.title = title; this.publishedAt = publishedAt; }
  public Long getId() { return id; }
  public String getTitle() { return title; }
  public Instant getPublishedAt() { return publishedAt; }
  public List<Comment> getComments() { return comments; }
  public List<Tag> getTags() { return tags; }
  public void addComment(String text) { comments.add(new Comment(this, text)); }
  public void addTag(Tag tag) { tags.add(tag); }
  public void removeTag(Long tagId) { tags.removeIf(tag -> tag.getId().equals(tagId)); }
}
