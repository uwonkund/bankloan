from django.db import models
from decimal import Decimal
from django.utils import timezone
from dateutil.relativedelta import relativedelta


class PaymentSchedule(models.Model):

    PAYMENT_STATUS = [
        ('pending',        'Pending'),
        ('paid',           'Paid'),
        ('overdue',        'Overdue'),
        ('partially_paid', 'Partially Paid'),
    ]

    loan          = models.ForeignKey(
        'loan.Loan',
        on_delete=models.CASCADE,
        related_name='payment_schedules',
    )
    month_number  = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='1 = January ... 12 = December'
    )
    due_date      = models.DateTimeField()
    amount_due    = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    interest_due  = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_due     = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    amount_paid   = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    balance       = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status        = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    is_paid       = models.BooleanField(default=False)
    paid_at       = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        ordering = ['due_date']

    def calculate_monthly_amounts(self):
        """
        Split the loan into 12 equal monthly payments.

        Formula:
            monthly_principal = loan.amount / 12
            monthly_interest  = loan.amount x (interest_rate / 100) / 12
            total_monthly_due = monthly_principal + monthly_interest

        Example — RWF 1,000,000 at 17%:
            monthly_principal = RWF 83,333.33
            monthly_interest  = RWF 14,166.67
            total_monthly_due = RWF 97,500.00
            total yearly      = RWF 1,170,000.00
        """
        loan              = self.loan
        principal         = Decimal(str(loan.amount))
        rate              = Decimal(str(loan.interest_rate)) / Decimal('100')
        monthly_principal = principal / Decimal('12')
        monthly_interest  = (principal * rate) / Decimal('12')
        total_monthly     = monthly_principal + monthly_interest

        self.amount_due   = monthly_principal.quantize(Decimal('0.01'))
        self.interest_due = monthly_interest.quantize(Decimal('0.01'))
        self.total_due    = total_monthly.quantize(Decimal('0.01'))
        self.balance      = self.total_due - self.amount_paid

    def mark_as_paid(self, amount_paid):
        """Mark this month as paid or partially paid."""
        self.amount_paid = Decimal(str(amount_paid))
        self.balance     = self.total_due - self.amount_paid

        if self.amount_paid >= self.total_due:
            self.is_paid = True
            self.status  = 'paid'
            self.paid_at = timezone.now()
        elif self.amount_paid > 0:
            self.status  = 'partially_paid'
        self.save()

    def check_overdue(self):
        """Mark as overdue if due date has passed and not yet fully paid."""
        if not self.is_paid and self.due_date < timezone.now():
            self.status = 'overdue'
            self.save()
            # Trigger penalty check immediately
            Penalty.apply_penalty(self)

    def save(self, *args, **kwargs):
        self.calculate_monthly_amounts()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Month {self.month_number} — "
            f"Due: RWF {self.total_due} on {self.due_date.strftime('%B %d, %Y')} "
            f"[{self.status}]"
        )


class Penalty(models.Model):

    PENALTY_TYPE = [
        ('late_payment',        'Late Payment — 5% added'),
        ('collateral_seizure',  'Collateral Seizure — 2 months missed'),
    ]

    PENALTY_STATUS = [
        ('active',   'Active'),
        ('resolved', 'Resolved'),
        ('seized',   'Collateral Seized'),
    ]

    schedule = models.ForeignKey(
        PaymentSchedule,
        on_delete=models.CASCADE,
        related_name='penalties',
    )
    loan = models.ForeignKey(
        'loan.Loan',
        on_delete=models.CASCADE,
        related_name='penalties',
        null=True,
        blank=True,
    )
    penalty_type    = models.CharField(max_length=30, choices=PENALTY_TYPE)
    penalty_rate    = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('5.00'),
        help_text='Penalty rate as percentage — default is 5%',
        null=True,
        blank=True,
    )
    original_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Original amount due before penalty',
        null=True,
        blank=True,
    )
    penalty_amount  = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='5% of the original amount due',
        null=True,
        blank=True,
    )
    total_amount_due = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Original amount + penalty amount',
        null=True,
        blank=True,
    )
    months_missed   = models.PositiveIntegerField(default=0)
    status          = models.CharField(max_length=20, choices=PENALTY_STATUS, default='active')
    applied_at      = models.DateTimeField(default=timezone.now)
    resolved_at     = models.DateTimeField(null=True, blank=True)
    note            = models.TextField(
        blank=True, null=True,
        help_text='Additional notes from bank staff',
    )
    created_at      = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        ordering = ['-applied_at']

    @classmethod
    def apply_penalty(cls, schedule):
        """
        Check the schedule and apply the correct penalty.

        Rule 1 — Late payment (1 month overdue):
            Add 5% to the amount due for that month.
            penalty_amount  = total_due x 5 / 100
            total_amount_due = total_due + penalty_amount

        Rule 2 — Collateral seizure (2 or more months missed):
            Flag the loan for collateral seizure.
            Bank staff will be notified to take action.
        """
        loan = schedule.loan

        # Count how many months are overdue for this loan
        overdue_schedules = PaymentSchedule.objects.filter(
            loan   = loan,
            status = 'overdue',
        ).count()

        # Check if penalty already exists for this schedule
        already_penalized = cls.objects.filter(
            schedule     = schedule,
            penalty_type = 'late_payment',
        ).exists()

        # ── Rule 1: Late payment — 1 month overdue ──
        if overdue_schedules >= 1 and not already_penalized:
            original_amount  = schedule.total_due
            penalty_amount   = (original_amount * Decimal('5')) / Decimal('100')
            total_amount_due = original_amount + penalty_amount

            cls.objects.create(
                schedule         = schedule,
                loan             = loan,
                penalty_type     = 'late_payment',
                penalty_rate     = Decimal('5.00'),
                original_amount  = original_amount,
                penalty_amount   = penalty_amount.quantize(Decimal('0.01')),
                total_amount_due = total_amount_due.quantize(Decimal('0.01')),
                months_missed    = overdue_schedules,
                status           = 'active',
                note             = (
                    f"Late payment penalty applied for Month {schedule.month_number}. "
                    f"Original: RWF {original_amount}, "
                    f"Penalty (5%): RWF {penalty_amount.quantize(Decimal('0.01'))}, "
                    f"New Total: RWF {total_amount_due.quantize(Decimal('0.01'))}."
                ),
            )

        # ── Rule 2: Collateral seizure — 2 or more months overdue ──
        if overdue_schedules >= 2:
            seizure_exists = cls.objects.filter(
                loan         = loan,
                penalty_type = 'collateral_seizure',
            ).exists()

            if not seizure_exists:
                cls.objects.create(
                    schedule         = schedule,
                    loan             = loan,
                    penalty_type     = 'collateral_seizure',
                    penalty_rate     = Decimal('0.00'),
                    original_amount  = schedule.total_due,
                    penalty_amount   = Decimal('0.00'),
                    total_amount_due = schedule.total_due,
                    months_missed    = overdue_schedules,
                    status           = 'seized',
                    note             = (
                        f"Client has missed {overdue_schedules} consecutive months. "
                        f"Collateral ({loan.collateral_type}) is subject to seizure. "
                        f"Bank staff must take immediate action."
                    ),
                )

                # Note: To flag the loan as defaulted, add a 'defaulted' status choice to Loan model
                # loan.status = 'defaulted'
                # loan.save()

    def resolve(self, note=None):
        """Mark penalty as resolved after client has paid."""
        self.status      = 'resolved'
        self.resolved_at = timezone.now()
        if note:
            self.note = note
        self.save()

    def __str__(self):
        loan_info = f"Loan {self.loan.id}" if self.loan else "No Loan"
        return (
            f"{self.get_penalty_type_display()} — "
            f"{loan_info} — "
            f"RWF {self.total_amount_due} [{self.status}]"
        )


class Payment(models.Model):

    PAYMENT_METHOD = [
        ('cash',          'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('mobile_money',  'Mobile Money'),
        ('cheque',        'Cheque'),
    ]

    PAYMENT_STATUS = [
        ('success', 'Success'),
        ('failed',  'Failed'),
        ('pending', 'Pending'),
    ]

    schedule = models.ForeignKey(
        PaymentSchedule,
        on_delete=models.CASCADE,
        related_name='payments',
        null=True,
        blank=True,
    )
    loan = models.ForeignKey(
        'loan.Loan',
        on_delete=models.CASCADE,
        related_name='payments',
    )
    amount_paid    = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD,
        default='cash',
        null=True,
        blank=True,
    )
    payment_date   = models.DateTimeField(default=timezone.now)
    status         = models.CharField(max_length=10, choices=PAYMENT_STATUS, default='pending')
    note           = models.TextField(blank=True, null=True)
    created_at     = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        ordering = ['-payment_date']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # After saving payment update the schedule
        if self.schedule:
            self.schedule.mark_as_paid(self.amount_paid)

            # If a penalty exists for this schedule resolve it after payment
            active_penalty = Penalty.objects.filter(
                schedule     = self.schedule,
                penalty_type = 'late_payment',
                status       = 'active',
            ).first()

            if active_penalty:
                active_penalty.resolve(
                    note=f"Resolved after payment of RWF {self.amount_paid} on {self.payment_date.strftime('%B %d, %Y')}."
                )

    def __str__(self):
        schedule_info = f"Month {self.schedule.month_number}" if self.schedule else "No Schedule"
        method = self.payment_method or "Unknown"
        return (
            f"Payment of RWF {self.amount_paid} "
            f"for {schedule_info} "
            f"via {method} [{self.status}]"
        )


def generate_payment_schedule(loan):
    """
    Auto-generate 12 monthly PaymentSchedule entries
    when a loan is approved.
    """
    PaymentSchedule.objects.filter(loan=loan).delete()

    start_date = loan.approval_date or timezone.now()

    for month in range(1, 13):
        due_date = start_date + relativedelta(months=month)
        PaymentSchedule.objects.create(
            loan         = loan,
            due_date     = due_date,
            month_number = month,
            amount_due   = Decimal('0.00'),
            is_paid      = False,
            status       = 'pending',
        )