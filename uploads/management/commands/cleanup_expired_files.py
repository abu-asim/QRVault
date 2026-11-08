from django.core.management.base import BaseCommand
from django.utils import timezone

from uploads.models import UploadedFile


class Command(BaseCommand):
    help = "Delete expired uploaded files from storage and database."

    def handle(self, *args, **options):
        expired_files = UploadedFile.objects.filter(
            expires_at__lte=timezone.now()
        )

        total = expired_files.count()
        deleted = 0
        failed = 0

        self.stdout.write(
            f"Found {total} expired file(s)."
        )

        for uploaded_file in expired_files.iterator():
            try:
                # Delete the physical file from storage.
                if uploaded_file.file:
                    uploaded_file.file.delete(save=False)

                # Delete the database record.
                uploaded_file.delete()

                deleted += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Deleted: {uploaded_file.original_name}"
                    )
                )

            except Exception as error:
                failed += 1

                self.stderr.write(
                    self.style.ERROR(
                        f"Failed: {uploaded_file.original_name} - {error}"
                    )
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Cleanup complete: {deleted} deleted, {failed} failed."
            )
        )