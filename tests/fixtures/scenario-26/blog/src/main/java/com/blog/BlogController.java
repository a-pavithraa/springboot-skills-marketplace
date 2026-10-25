package com.blog;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.List;
@RestController @RequestMapping("/api/posts")
class BlogController {
  private final PostService service;
  BlogController(PostService service) { this.service = service; }
  @GetMapping List<PostService.PostView> feed() { return service.feed(); }
  @DeleteMapping("/{postId}/tags/{tagId}") ResponseEntity<Void> removeTag(@PathVariable Long postId, @PathVariable Long tagId) {
    service.removeTag(postId, tagId); return ResponseEntity.noContent().build();
  }
  @DeleteMapping("/{postId}") ResponseEntity<Void> delete(@PathVariable Long postId) {
    service.delete(postId); return ResponseEntity.noContent().build();
  }
}
