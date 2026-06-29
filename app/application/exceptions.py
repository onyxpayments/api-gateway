class PaymentRequestUnavailable(RuntimeError):
    pass


class PaymentRequestRejected(RuntimeError):
    def __init__(self, status_code: int, detail):
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


class InvalidPaymentRequestResponse(RuntimeError):
    pass
