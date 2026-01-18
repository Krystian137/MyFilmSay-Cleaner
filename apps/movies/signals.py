from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Vote

@receiver(post_save, sender=Vote)
def update_vote_count_on_create(sender, instance, created, **kwargs):
    if created:
        comment = instance.comment
        if instance.vote_type == 'like':
            comment.likes_count += 1
        else:
            comment.dislikes_count += 1
        comment.save(update_fields=['likes_count', 'dislikes_count'])

@receiver(post_delete, sender=Vote)
def update_vote_count_on_delete(sender, instance, **kwargs):
    comment = instance.comment
    if instance.vote_type == 'like':
        comment.likes_count -= 1
    else:
        comment.dislikes_count -= 1
    comment.save(update_fields=['likes_count', 'dislikes_count'])