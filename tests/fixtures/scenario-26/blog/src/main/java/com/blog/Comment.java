package com.blog;
import jakarta.persistence.*;
@Entity @Table(name = "comments")
public class Comment {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
  @ManyToOne(fetch = FetchType.LAZY) private Post post;
  private String text;
  protected Comment() {}
  Comment(Post post, String text) { this.post = post; this.text = text; }
  public Long getId() { return id; }
  public Post getPost() { return post; }
  public String getText() { return text; }
}
