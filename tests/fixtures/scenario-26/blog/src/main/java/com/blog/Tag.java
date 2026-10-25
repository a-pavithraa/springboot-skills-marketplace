package com.blog;
import jakarta.persistence.*;
/** A tag is shared by many posts. */
@Entity @Table(name = "tags")
public class Tag {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
  @Column(unique = true) private String name;
  protected Tag() {}
  public Tag(String name) { this.name = name; }
  public Long getId() { return id; }
  public String getName() { return name; }
}
