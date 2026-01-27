from .base import (
    FilingStatus, TaxpayerType, Address, Person, Dependent, BankAccount
)
from .income import (
    W2, Form1099INT, Form1099DIV, Form1099R, Form1099NEC, Form1099G,
    FormK1_1065, FormK1_1120S, SSA1099, FormFBAR, Form1099MISC, ScheduleE
)
from .deductions import Form1098, Form1095A
from .return_data import IncomeData, DeductionData, TaxReturn
