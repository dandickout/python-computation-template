# Imports
import logging
import json
import os
from pymongo import MongoClient
from conversions import volume_conversion_factor_from_to

# Logger settings - CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

url = os.environ['MONGO_URL']
# Set client
client = MongoClient(url)
# Set database
db_name = os.environ['MONGODB']
db = client[db_name]
method_name = os.environ['AWS_LAMBDA_FUNCTION_NAME']
dec_places = int(os.environ['DECIMAL_PLACES'])

# Doesnt not like string
# Class to hold the decisions
class DecisionValue:

    def __init__(self, value):
        try:
            self._value = float(value)
        except:
            raise ValueError("Value must be a number")
            
    def get(self):
        return self._value
    
    @property
    def value(self):
        return self._value
    
    # @value.setter
    # def value(self, value):
    #     # Check if value is a number is instance float/int
    #     if value.isnumeric() or value.isdecimal():
    #         raise ValueError("Value must be a number")
    #     self._value = float(value)

# Class to hold the decision units 
class DecisionUnit:
    def __init__(self, unit):
        if len(unit) <= 0:
            raise ValueError("Unit cannot be None")
        self._unit = unit
    
    def get(self):
        return self._unit
    
    @property
    def unit(self):
        return self._unit
    
    # @unit.setter
    # def unit(self, unit):
    #     if(unit is None):
    #         raise ValueError("Unit cannot be None")
    #     self._unit = str(unit)

    def __str__(self):
        return f"{self.unit}"

# Class to hold the decisions
class Decision:
    def __init__(self, decision):
        if(decision is None):
            raise ValueError("Decision cannot be None")
        self._decision = decision
    
    def get(self):
        return self._decision

    def __str__(self):
        return f"{self._decision}"

    @property
    def decision(self):
        return self._decision
    
    # @decision.setter
    # def decision(self, decision):
    #     if(decision is None):
    #         raise ValueError("Decision cannot be None")
    #     self._decision = str(decision)

class Decisions:
    def __init__(self, 
        decision1, 
        decision2, 
        #decision2_value, 
        #decision2_unit, 
        decision3, 
        #decision3_value, 
        #decision3_unit, 
        decision4, 
        decision4_value, 
        decision4_unit, 
        decision5,
        #decision5_value, 
        #decision5_unit, 
        #decision6,
        #decision6_value, 
        #decision6_unit, 
        ):
        self.decision1 = Decision(decision1)
        self.decision2 = Decision(decision2)
        self.decision3 = Decision(decision3)
        self.decision4 = Decision(decision4)
        self.volume = DecisionValue(decision4_value)
        self.unit = DecisionUnit(decision4_unit)
        self.decision5 = Decision(decision5)
        # self.decision6 = Decision(decision6)  # Not used
    def __str__(self):
        return f"Decision1: {self.decision1}, \
                    Decision2: {self.decision2}, \
                    Decision3: {self.decision3}, \
                    Decision4: {self.decision4}, \
                    Decision5: {self.decision5}"
                    # Decision6: {self.decision6}"

#===================================================================================================
# MAIN FUNCTION HANDLER
#===================================================================================================
def lambda_handler(event, context):
    context.callbackWaitsForEmptyEventLoop = False
    print(event)

    logger.info("Received event: " + str(event))
    factorscoll = db.get_collection('factors')

    status = 500
    # Transfer the event to a class
    # ++ Process Prep ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    try:
        incDecisions = Decisions(
            event['Decision1'], 
            event['Decision2'], 
            #event['Decision2_value'],
            #event['Decision2_unit'],
            event['Decision3'], 
            #event['Decision3_value'],
            #event['Decision3_unit'],
            event['Decision4'], 
            event['Decision4_value'], 
            event['Decision4_unit'],
            event['Decision5'],
            #event['Decision5_value'],
            #event['Decision5_unit'],
            #event['Decision6'],
            #event['Decision6_value'],
            #event['Decision6_unit']
            )
    except ValueError as e:
        body = {
            "message": e,
        }
        return {
            'statusCode': status,
            'body': json.dumps(body, default=str)
        }
   # ++ Process Method ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    factors = factorscoll.find_one({
        "Decision1": incDecisions.decision1.get(), 
        "Decision2": incDecisions.decision2.get(), 
        "Decision3": incDecisions.decision3.get(), 
        "Decision4": incDecisions.decision4.get(), 
        "Decision5": incDecisions.decision5.get(),
        # "Decision6": incDecisions.decision6.get()
        })

    if factors is None:
        response = "method not found in database"
        return {
            'statusCode': status,
            'body': response
        }
    logger.info(factors)

    # Get the volume and unit
    unit = incDecisions.unit.get()
    volume = incDecisions.volume.get()
    Dunit = factors['Dunit']

    # convert the volume to our base unit    
    converted_volume = volume* volume_conversion_factor_from_to(unit, Dunit)
        
    logger.info(str(converted_volume))

    # convert the volume in base units to output values in kilograms
    conversion1_in_kg = factors['factor_1'] * converted_volume
    conversion2_in_kg = factors['factor_2'] * converted_volume
    conversion3_in_kg = factors['factor_3'] * converted_volume

    logger.info(str(converted_volume) + " " + str(conversion1_in_kg) +
                " " + str(conversion2_in_kg) + " " + str(conversion3_in_kg))
                
    # ++ Prepare the Response ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    status = 200
    response_dict = {
        "transaction_guid": event['transaction_guid'],
        "method_name": method_name,
        "calculate_data": {
            "conversion1_kg": round(conversion1_in_kg, dec_places),
            "conversion2_kg": round(conversion2_in_kg, dec_places),
            "conversion3_kg": round(conversion3_in_kg, dec_places),
            "category": factors['Category'],
            "year": factors['Year'],
            "factor_1": factors['factor_1'],
            "factor_2": factors['factor_2'],
            "factor_3": factors['factor_3'],
            "link": factors['Link'],
            "volume": incDecisions.volume.get(),
            "type": incDecisions.decision4.get(),
            "unit": incDecisions.unit.get()
        },
    }

    response = response_dict
    logger.info(response)

    return {
        'statusCode': status,
        'body': response,
    }
