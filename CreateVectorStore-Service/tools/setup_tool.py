from tools.booking_toor import booking_user_form_tool
from tools.check_available_time_slot import checkTime
from tools.general_info import general_info
from tools.email_chain import send_email_tool
from tools.check_for_details import check_details
from langchain.tools import  StructuredTool
from tools.cancelBooking import CancelBooking
from tools.rescheduleBooking import RescheduleBooking
from tools.postGatedLead import PostLeadGated
from tools.get_another_club import GetAnotherClub
from langchain_core.utils.function_calling import convert_to_openai_function
from tools.rescheduleTimeSlot import checkRescheduledTime
from tools.get_location import BookTourWebJson
import asyncio
from pydantic import BaseModel, create_model, Field
from concurrent.futures import ThreadPoolExecutor

class QueryInput(BaseModel):
    query: str = Field(description="Query to be passed as an argument. Always use this")

class AnotherClubInput(BaseModel):
    query:str = Field(description="User Query or Question to be passed as an argument")
    locationname: str = Field(description="Location of the Club whose information the user wants")

class EmailInput(BaseModel):
    query: str = Field(description="Name of the topic of the subject that is to be sent to the user")
    email: str = Field(description="Email address of the user")

class TimeInput(BaseModel):
    query: str = Field(description="Date and Time mentioned by the user")
    time_slots: str = Field(description="Available Time slots for booking")

class DateInput(BaseModel):
    query: str = Field(description="Query to be passed as an argument")
    date: str = Field(description="User's requested date for booking. Must be in YYYY-MM-DD format.")
    time: str = Field(description="User's requested time for booking")


class BookingInput(BaseModel):
    date:str = Field(description="Date that was collected for booking")
    time:str = Field(description="Time that was collected for booking")
    firstname: str = Field(description="First name of the user")
    lastname: str = Field(description="Last name of the user")
    email: str = Field(description="Email address of the user")
    phonenumber: str = Field(description="Phone number of the user")

class GatedPricingInput(BaseModel):
    firstname: str = Field(description="First name of the user")
    lastname: str = Field(description="Last name of the user")
    email: str = Field(description="Email Address of the user")
    phonenumber:str = Field(description="Phone number of the user")

class RescheduleBookingInput(BaseModel):
    date:str = Field(description="Date that was collected for reschedule booking")
    time:str = Field(description="Time that was collected for reschedule booking")



def dynmaic_json(field_descriptions):
    all_model_fields = {
        field: (str, Field(description=description))
        for field, description in field_descriptions.items()
    }
    all_model_fields['visit_type'] = (str, Field(..., description="Type of visit"))
    DynamicModel = create_model('DynamicModel', **all_model_fields)
    return DynamicModel

class GetCustomTools():
    
    tools=[]

    def __init__(self, params=None):
        self.params = params
        self.DynamicBookingModel = dynmaic_json(self.params.booking_tour_fields) if self.params else None
        self.Gated = self.params.type if self.params else None
        self.Booked_Flag = self.params.flagBooked if self.params else None
        self.Branch = self.params.branch if self.params else None
        self.gdpr = self.params.gdpr if self.params else None
    
    @classmethod
    async def create(cls, params=None):
        self = cls(params)
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)
        await asyncio.get_event_loop().run_in_executor(
            executor, asyncio.run, self._initialize_tools_threadsafe()
        )
        return self


    async def _initialize_tools_threadsafe(self):

        check_time_slot_reschedule_tool = StructuredTool.from_function(
            name="checkTime",
            coroutine= await checkRescheduledTime(self.params),
            description="A tool used to check the availability of the request date for rescheduling of booking",
            args_schema=TimeInput
        )
        print("Entered hereeee")
        
        check_time_slot_tool = StructuredTool.from_function(
            name='checkTime',
            coroutine= await checkTime(self.params),
            description="A tool used to check the availability of the requested date for booking",
            args_schema=TimeInput
        )
        

        collect_details_booking = StructuredTool.from_function(
            name='bookTool',
            coroutine= await booking_user_form_tool(self.params),
            description="A tool used to book a tour/trials/pass/visit once the user details are confirmed",
            args_schema=self.DynamicBookingModel
        )

        general_info_tool = StructuredTool.from_function(
            name='generalInfo',
            coroutine= await general_info(self.params),
            description="Use this tool for any queries related to the fitness club related queries, classes, memberships, age requirements,   payments, gym, personal training sessions, sports and massage therapy, member benefits, freezing memberships, changing membership types, cancellation policies, team members, club managers, Personal training, etc",
            args_schema=QueryInput
        )

        # email_send_tool = StructuredTool.from_function(
        #     name="EmailTool",
        #     func = send_email_tool(self.params),
        #     description="Use this tool to send the necessary response through email if the user requests it, except for Tour Booking.",
        #     args_schema=EmailInput
        # )

        check_details_tool = StructuredTool.from_function(
            name="check_details",
            coroutine =  await check_details(self.params),
            description="A tool used to Check for available user details before you ask the detail from the user",
            args_schema=QueryInput
        )

        cancel_booking_tool = StructuredTool.from_function(
            name="CancelBookTool",
            coroutine= await CancelBooking(self.params),
            description="A tool used to cancel a booked tour/trial/pass/visits",
            args_schema=QueryInput
        )

        reschedule_booking_tool = StructuredTool.from_function(
            name="RescheduleTourBook",
            coroutine= await RescheduleBooking(self.params),
            description="A tool used to reschedule tour/trial/pass/booking booking",
            args_schema=RescheduleBookingInput
        )

        postGated_tool = StructuredTool.from_function(
            name="PostLeadTool",
            coroutine= await PostLeadGated(self.params),
            description="A tool used to record the details of newly obtained details",
            args_schema=GatedPricingInput
        )

        # anotherClub_tool = StructuredTool.from_function(
        #     name="AnotherClubInquiry",
        #     func=GetAnotherClub(self.params),
        #     description="A tool that is used to provide information of another Club",
        #     args_schema=AnotherClubInput

        # )

        LocationBranch_tool = StructuredTool.from_function(
            name="bookTool",
            coroutine= await BookTourWebJson(self.params),
            description="A tool used to book a tour/trials/pass/visit",
            args_schema = QueryInput,
            return_direct=True
        )

       
        # self.tools=[check_time_slot_tool,collect_details_booking,general_info_tool,email_send_tool,check_details_tool,gated_pricing_tool]
        self.tools = [general_info_tool]
        if self.Branch:
            if self.Booked_Flag:
                self.tools.extend([cancel_booking_tool,reschedule_booking_tool,check_time_slot_reschedule_tool])
            else:
                self.tools.extend([check_details_tool,collect_details_booking,check_time_slot_tool]) #anotherClub_tool,
        else:
            self.tools.append(LocationBranch_tool)
        if self.Gated == "gated":
            self.tools.append(postGated_tool)

    async def get_tools(self):
        return self.tools
    
    async def get_tools_names(self):
        return [tool.name for tool in self.tools]
    
    async def get_openai_functions(self):
        tools = self.get_tools()
        open_ai_functions= [convert_to_openai_function(tool) for tool in tools ]
        return open_ai_functions
    