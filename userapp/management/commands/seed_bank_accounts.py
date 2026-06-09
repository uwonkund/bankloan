from django.core.management.base import BaseCommand
from userapp.models import BankAccount


BANK_ACCOUNTS = [
    'ACC-001001', 'ACC-001002', 'ACC-001003', 'ACC-001004', 'ACC-001005',
    'ACC-001006', 'ACC-001007', 'ACC-001008', 'ACC-001009', 'ACC-001010',
    'ACC-001011', 'ACC-001012', 'ACC-001013', 'ACC-001014', 'ACC-001015',
    'ACC-001016', 'ACC-001017', 'ACC-001018', 'ACC-001019', 'ACC-001020',
]


class Command(BaseCommand):
    help = 'Seed the database with bank-assigned account numbers'

    def handle(self, *args, **kwargs):
        created = 0
        for acc in BANK_ACCOUNTS:
            _, was_created = BankAccount.objects.get_or_create(account_number=acc)
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(
            f'Successfully seeded {created} bank account numbers.'
        ))
