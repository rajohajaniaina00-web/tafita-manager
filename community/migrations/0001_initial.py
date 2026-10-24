import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contributions', '0001_initial'),
        ('events', '0002_event_end_date_alter_event_date'),
        ('members', '0003_member_activation_code'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CommunityPost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(blank=True, max_length=5000, verbose_name='Texte')),
                ('image', models.ImageField(blank=True, null=True, upload_to='community/posts/%Y/%m/', verbose_name='Image')),
                ('status', models.CharField(choices=[('pending', 'En attente'), ('approved', 'Publiée'), ('rejected', 'Refusée')], default='pending', max_length=12, verbose_name='Statut')),
                ('moderation_note', models.CharField(blank=True, max_length=300, verbose_name='Note de modération')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Créée le')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Modifiée le')),
                ('moderated_at', models.DateTimeField(blank=True, null=True, verbose_name='Modérée le')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='community_posts', to=settings.AUTH_USER_MODEL)),
                ('moderated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='moderated_community_posts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Publication communautaire',
                'verbose_name_plural': 'Publications communautaires',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('general', 'Discussion générale'), ('direct', 'Discussion privée'), ('group', 'Groupe')], default='group', max_length=10)),
                ('title', models.CharField(max_length=140, verbose_name='Titre')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_activity', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_tafita_conversations', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-last_activity'],
            },
        ),
        migrations.CreateModel(
            name='ConversationMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.CharField(max_length=4000, verbose_name='Message')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Envoyé le')),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='community.conversation')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tafita_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at', 'id'],
            },
        ),
        migrations.CreateModel(
            name='ConversationParticipant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('last_read_at', models.DateTimeField(blank=True, null=True)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participant_links', to='community.conversation')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversation_memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['joined_at'],
            },
        ),
        migrations.AddField(
            model_name='conversation',
            name='participants',
            field=models.ManyToManyField(related_name='tafita_conversations', through='community.ConversationParticipant', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='EventComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.CharField(max_length=1500, verbose_name='Commentaire')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Publié le')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='community_event_comments', to=settings.AUTH_USER_MODEL)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='community_comments', to='events.event')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='EventReaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reaction', models.CharField(default='love', editable=False, max_length=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='community_reactions', to='events.event')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='community_event_reactions', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='MemberInvitation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=80, unique=True, verbose_name='Code d’activation')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Créé le')),
                ('expires_at', models.DateTimeField(verbose_name='Expire le')),
                ('used_at', models.DateTimeField(blank=True, null=True, verbose_name='Utilisé le')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_member_invitations', to=settings.AUTH_USER_MODEL)),
                ('member', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='community_invitation', to='members.member', verbose_name='Membre')),
            ],
            options={
                'verbose_name': 'Invitation de membre',
                'verbose_name_plural': 'Invitations de membres',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='MemberPaymentSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.PositiveBigIntegerField(verbose_name='Montant déclaré (Ar)')),
                ('method', models.CharField(choices=[('cash', 'Espèces'), ('mobile_money', 'Mobile Money'), ('bank', 'Virement bancaire'), ('other', 'Autre')], max_length=30, verbose_name='Mode de paiement')),
                ('reference', models.CharField(blank=True, max_length=100, verbose_name='Référence')),
                ('proof', models.FileField(blank=True, null=True, upload_to='community/payment-proofs/%Y/%m/', validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp', 'pdf'])], verbose_name='Justificatif (image ou PDF)')),
                ('notes', models.CharField(blank=True, max_length=500, verbose_name='Note complémentaire')),
                ('status', models.CharField(choices=[('pending', 'En attente de vérification'), ('approved', 'Validé'), ('rejected', 'Refusé')], default='pending', max_length=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('rejection_reason', models.CharField(blank=True, max_length=300)),
                ('contribution', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='member_submissions', to='contributions.contribution', verbose_name='Cotisation')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_member_payment_submissions', to=settings.AUTH_USER_MODEL)),
                ('submitted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='member_payment_submissions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Déclaration de paiement membre',
                'verbose_name_plural': 'Déclarations de paiement membres',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PostComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.CharField(max_length=1500, verbose_name='Commentaire')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Publié le')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='community_post_comments', to=settings.AUTH_USER_MODEL)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='community.communitypost')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='PostReaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reaction', models.CharField(default='love', editable=False, max_length=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reactions', to='community.communitypost')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='community_post_reactions', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name='communitypost',
            index=models.Index(fields=['status', '-created_at'], name='community_c_status_012a6e_idx'),
        ),
        migrations.AddIndex(
            model_name='conversationmessage',
            index=models.Index(fields=['conversation', 'id'], name='community_c_convers_c49199_idx'),
        ),
        migrations.AddConstraint(
            model_name='conversationparticipant',
            constraint=models.UniqueConstraint(fields=('conversation', 'user'), name='unique_user_per_tafita_conversation'),
        ),
        migrations.AddConstraint(
            model_name='conversation',
            constraint=models.UniqueConstraint(condition=models.Q(('kind', 'general')), fields=('kind',), name='one_general_tafita_conversation'),
        ),
        migrations.AddConstraint(
            model_name='eventreaction',
            constraint=models.UniqueConstraint(fields=('event', 'user'), name='unique_event_reaction_per_user'),
        ),
        migrations.AddIndex(
            model_name='memberpaymentsubmission',
            index=models.Index(fields=['status', '-created_at'], name='community_m_status_696285_idx'),
        ),
        migrations.AddConstraint(
            model_name='postreaction',
            constraint=models.UniqueConstraint(fields=('post', 'user'), name='unique_post_reaction_per_user'),
        ),
    ]
