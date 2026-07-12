class BaseAgent:

    name="BaseAgent"

    def execute(self,task):

        return {

            "agent":self.name,

            "task":task,

            "status":"completed"

        }
