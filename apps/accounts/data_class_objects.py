from dataclasses import dataclass
from datetime import datetime
from rest_framework_dataclasses.serializers import DataclassSerializer


@dataclass
class OtpStructureDTO:
    otp: int
    created_time: datetime.time


@dataclass
class RequestOtpStructureDTO:
    remaining_time: int
    is_send_before: bool

class OutputRequestOtpSerializer(DataclassSerializer):
    class Meta:
        dataclass = RequestOtpStructureDTO
        fields = ['remaining_time', 'is_send_before']



@dataclass
class MessageDTO:
    message: str


class MessageOutputSerializer(DataclassSerializer):
    class Meta:
        dataclass = MessageDTO
        fields = ("message",)
