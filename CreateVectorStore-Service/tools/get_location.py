

async def BookTourWebJson(self):
    async def BookAtour(query:str):
        self.WantsLocation=True
        if self.agent.lower() not in ["facebook", "fb"]:
            return "Please Select The Club from the Dropdown Box below"
        else:
            return "Please Select the Club"
    return BookAtour