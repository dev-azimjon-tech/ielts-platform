import json

from .database import get_db


READING_PASSAGES = [
    {
        "title": "The Hidden Life of Urban Trees",
        "body": """When a city plants a tree, the visible part is only a small piece of the project. Below the pavement, the tree needs room for roots, air, water, and living organisms. In a natural forest, roots can spread through soft ground, but a street tree often has to share a narrow space with roads, pipes, cables, and building foundations. Its survival depends on decisions made long before the first leaves appear.

Urban tree selection is therefore more complicated than choosing the fastest-growing species. Planners consider the mature height of a tree, the width of its canopy, the strength of its branches, and its ability to tolerate heat or poor soil. They also try to avoid planting one species along an entire street. A disease that affects one species can move quickly through a uniform population, while a mixture of species is more likely to contain some trees that can resist it.

One increasingly common solution to the problem of limited root space is the soil-cell system. Strong underground frames are placed beneath a pavement. The frames support the weight of people and vehicles above them, while the spaces between them are filled with soil. Roots can then grow through a larger volume without lifting the pavement. The system is more expensive than an ordinary planting pit, but it can reduce repair costs later.

Trees also change the temperature of a street. Their leaves block some direct sunlight, and they release water vapour through a process called transpiration. Together, shade and transpiration can make a planted street feel cooler than a nearby street with no trees. The effect is strongest when trees are healthy and have enough water. A young tree, however, may need regular watering during its first three summers before its root system is established.

Care does not end when a tree is planted. Pruning may be needed to remove dangerous branches, but excessive pruning can weaken a tree. Staff must also check for disease, protect the trunk from damage, and keep the soil from becoming completely sealed by paving. In some cities, residents help by recording the dates when trees flower or by reporting broken branches through a public website. These observations give planners useful information between formal inspections.

The work of planting trees is often shared by several departments. Parks staff may choose the species, road engineers may design the pavement, and utility companies may identify underground services. Good plans leave enough space for roots while protecting pipes and cables. The aim is not simply to place more trees on a map. It is to create streets where trees can grow for decades and continue to provide shade, habitat, and cleaner air.""",
        "questions": [
            {"type": "multiple_choice", "prompt": "What is the main purpose of the passage?", "options": ["To compare the prices of different tree species", "To explain how cities can help trees survive and provide benefits", "To show that forests are more useful than streets", "To argue that all pavements should be removed"], "answer": "B", "explanation": "The passage describes the planning, planting, and care needed for healthy urban trees."},
            {"type": "tfng", "prompt": "Urban trees usually grow in more spacious soil than trees in natural forests.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "FALSE", "explanation": "The passage contrasts the soft, open ground of a forest with the narrow spaces available to street trees."},
            {"type": "short_answer", "prompt": "What part of a street tree is often affected by paving?", "options": [], "answer": "roots", "explanation": "The opening paragraph focuses on the limited space available for roots below pavements."},
            {"type": "multiple_choice", "prompt": "What is the main advantage of a soil-cell system?", "options": ["It makes trees grow twice as fast.", "It gives roots more room beneath a surface that can still carry weight.", "It removes the need for watering.", "It prevents all diseases from reaching trees."], "answer": "B", "explanation": "The frames support the pavement while allowing roots to use a larger volume of soil."},
            {"type": "short_answer", "prompt": "What process releases water vapour from tree leaves?", "options": [], "answer": "transpiration", "explanation": "The passage names transpiration as the process that releases water vapour."},
            {"type": "tfng", "prompt": "Every urban tree species is selected because it grows very quickly.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "NOT GIVEN", "explanation": "The passage says planners consider many characteristics, but it does not say every species is selected for fast growth."},
            {"type": "multiple_choice", "prompt": "Why do planners avoid planting one species along an entire street?", "options": ["One species usually produces too much shade.", "Mixed species require less space.", "A disease may spread quickly through a uniform population.", "Residents prefer streets with different colours."], "answer": "C", "explanation": "Species diversity makes it more likely that some trees can resist a disease."},
            {"type": "short_answer", "prompt": "During how many first summers may a young tree need regular watering?", "options": [], "answer": "three", "explanation": "A young tree may need regular watering during its first three summers."},
            {"type": "tfng", "prompt": "The passage says pruning is never necessary for urban trees.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "FALSE", "explanation": "Pruning may be needed to remove dangerous branches, although excessive pruning can be harmful."},
            {"type": "multiple_choice", "prompt": "What can residents record to help city planners?", "options": ["The dates when trees flower", "The height of every building", "The number of cars on each street", "The brand of paving used nearby"], "answer": "A", "explanation": "Residents may record flowering dates or report broken branches through a public website."},
            {"type": "short_answer", "prompt": "What underground service competes with tree roots for space? Give one example.", "options": [], "answer": "pipes", "explanation": "The passage mentions pipes and cables as underground services competing for space."},
            {"type": "tfng", "prompt": "A tree's cooling effect depends only on the height of its trunk.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "FALSE", "explanation": "Cooling is connected to shade, transpiration, tree health, and water availability."},
            {"type": "multiple_choice", "prompt": "What does the final paragraph suggest about urban tree planting?", "options": ["It is mainly a responsibility for parks staff.", "It succeeds when trees are planted as close together as possible.", "It should focus only on the number of trees planted.", "It requires cooperation and long-term planning."], "answer": "D", "explanation": "The final paragraph describes cooperation between parks staff, road engineers, and utility companies."},
        ],
    },
    {
        "title": "Bringing a River Back to the Surface",
        "body": """For much of the twentieth century, the Marlow Brook was invisible. The small river once crossed the centre of Bellford, but after a series of floods in 1968 it was placed inside a concrete culvert and covered by a car park. The decision solved an immediate problem and created more space for vehicles. Over time, however, residents forgot that water was moving beneath them.

The brook became visible again after a major storm in 2006. Rain filled the culvert faster than it could carry water, and several streets were flooded. An investigation found that the covered channel had very little room to expand during heavy rain. The council began looking for a solution that would reduce flood risk while also improving the centre of the town.

The restoration project started in 2012. Before any construction began, engineers used historic maps, ground surveys, and small cameras to locate the old route. The team then removed a section of concrete and created a shallow channel with gentle bends. Stone shelves were placed at the edges so that plants could grow above the normal water level. Wetland terraces were added to hold some rainwater temporarily, slowing the flow into the main channel.

The design required more than an engineering plan. The council had to buy part of an abandoned warehouse site, move a cycle route, and protect a footbridge used by schoolchildren. Some residents were worried that an open river would attract litter or insects. Others supported the project because the car park had become an unpleasant area with little shade. Meetings with local groups led to a wider path, more lighting, and bins near the busiest entrance.

Scientists began monitoring the brook as soon as the first plants were established. They measured water temperature, dissolved oxygen, and the number of aquatic invertebrates. The return of mayfly larvae was considered encouraging because these insects are sensitive to poor water quality. Fish were not released from another river; instead, small fish returned naturally after conditions improved.

The project has not recreated the exact river that existed before 1968. The surrounding roads, buildings, and flood controls are different from those of the past. Its purpose is to create a new balance in which water can move safely, wildlife can find habitat, and people can see the river again. The Marlow Brook demonstrates that urban restoration is often less about returning to an original state than about designing a workable future.""",
        "questions": [
            {"type": "multiple_choice", "prompt": "Why was the Marlow Brook placed inside a culvert in 1968?", "options": ["To create a fish habitat", "To reduce the immediate problem of flooding and create parking space", "To make the water easier for scientists to study", "To connect it to a new railway"], "answer": "B", "explanation": "The culvert followed flooding and created more room for vehicles."},
            {"type": "short_answer", "prompt": "In what year did a major storm reveal the weakness of the covered channel?", "options": [], "answer": "2006", "explanation": "The passage says the brook became visible again after a major storm in 2006."},
            {"type": "tfng", "prompt": "The Marlow Brook had never flooded before the restoration project was planned.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "FALSE", "explanation": "The brook had flooded in 1968 and again in 2006."},
            {"type": "multiple_choice", "prompt": "What did engineers do before construction started?", "options": ["They released fish into the channel.", "They built the footbridge.", "They located the old route using maps, surveys, and cameras.", "They removed all the nearby roads."], "answer": "C", "explanation": "Historic maps, ground surveys, and small cameras were used to locate the old route."},
            {"type": "short_answer", "prompt": "What material was removed to make part of the brook visible again?", "options": [], "answer": "concrete", "explanation": "The team removed a section of the concrete culvert."},
            {"type": "multiple_choice", "prompt": "What is one function of the wetland terraces?", "options": ["They increase the speed of the river.", "They hold some rainwater temporarily.", "They provide underground parking.", "They prevent plants from growing near the water."], "answer": "B", "explanation": "The terraces hold rainwater temporarily and slow its movement into the main channel."},
            {"type": "tfng", "prompt": "All local residents supported the restoration design from the beginning.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "NOT GIVEN", "explanation": "The passage describes different views but does not say all residents supported or opposed the plan."},
            {"type": "short_answer", "prompt": "What aspect of the water did scientists measure as part of their monitoring?", "options": [], "answer": "dissolved oxygen", "explanation": "Scientists measured water temperature, dissolved oxygen, and aquatic invertebrates."},
            {"type": "multiple_choice", "prompt": "Why was the return of mayfly larvae encouraging?", "options": ["They are easy to catch.", "They are a source of food for residents.", "They are sensitive to poor water quality.", "They prevent all flooding."], "answer": "C", "explanation": "Mayfly larvae are sensitive to poor water quality, so their return suggested improvement."},
            {"type": "tfng", "prompt": "Fish were transported from another river into the restored brook.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "FALSE", "explanation": "The passage says fish returned naturally and were not released from another river."},
            {"type": "short_answer", "prompt": "What type of route did the council move to accommodate the restoration?", "options": [], "answer": "cycle route", "explanation": "The council moved a cycle route as part of the design."},
            {"type": "multiple_choice", "prompt": "What concern did some residents have about an open river?", "options": ["It would make the town too quiet.", "It might attract litter or insects.", "It would remove all public lighting.", "It would stop children walking to school."], "answer": "B", "explanation": "Some residents worried that an open river would attract litter or insects."},
            {"type": "multiple_choice", "prompt": "What is the main lesson of the Marlow Brook project?", "options": ["Urban rivers should always be covered.", "Restoration should copy the past exactly.", "Urban restoration can create a workable balance for the future.", "Flood control and wildlife cannot exist together."], "answer": "C", "explanation": "The conclusion says the project is about designing a workable future rather than recreating the past exactly."},
        ],
    },
    {
        "title": "Why Some Bees Live Alone",
        "body": """When people hear the word bee, they often imagine a large colony with a queen, workers, honey, and a hive. That description fits the honey bee, but it does not describe most bee species. Many bees are solitary. Each female builds her own nest, collects food for her young, and completes the nesting cycle without a permanent colony.

The nesting place depends on the species. Mining bees dig tunnels in bare or lightly covered soil. Mason bees use mud to close the chambers in a small cavity. Leafcutter bees cut pieces from leaves and use them to line their nests. Hollow plant stems, gaps in old walls, and small holes in dry wood can all become useful nesting sites. A garden that looks untidy in a few corners may therefore offer more habitat than a perfectly sealed lawn.

A female solitary bee usually creates a series of separate chambers. She carries pollen and nectar to one chamber, shapes it into a food ball, and lays a single egg on it. She then closes the chamber and begins another. The young bee develops alone and does not receive care from its mother after the nest is sealed. In many species, males emerge earlier than females, often because they wait near the nest entrances for females to appear.

Solitary bees are important pollinators. They do not generally carry pollen in the same neat baskets that honey bees use. Instead, pollen may stick to hairs on the underside of the body or on the legs. A bee that visits many flowers can move pollen between plants even when it is collecting food for only one nest. Farmers and gardeners are increasingly interested in these small visitors because reliable pollination can improve the production of fruit and seeds.

Gardens can support solitary bees without becoming complicated. A long flowering season is useful because different bee species are active at different times. Native flowering plants, a small patch of bare soil, and stems that remain standing over winter can provide food and nesting places. Chemical pesticides can harm bees directly, so gardeners are encouraged to use them carefully and only when necessary. A shallow dish of water with stones can also offer a safe drinking place.

The solitary lifestyle does not mean that these bees are unimportant or unprotected by nature. It simply means their needs are less visible than those of a colony. By leaving a few suitable spaces and allowing flowers to bloom across the season, a city garden can provide a surprising amount of habitat. Small changes are often enough to make a difference to pollinators that live alone.""",
        "questions": [
            {"type": "multiple_choice", "prompt": "What is the main focus of the passage?", "options": ["How honey is collected from large hives", "The lives of solitary bees and ways to support them", "Why lawns are better than gardens", "The history of commercial farming"], "answer": "B", "explanation": "The passage explains solitary bee behaviour, nesting, pollination, and habitat needs."},
            {"type": "tfng", "prompt": "All bee species live in large colonies with a queen.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "FALSE", "explanation": "The passage says many bee species are solitary and do not live in permanent colonies."},
            {"type": "short_answer", "prompt": "What two foods does a female bee place in a nest chamber?", "options": [], "answer": "pollen and nectar", "explanation": "The female shapes pollen and nectar into a food ball for the egg."},
            {"type": "multiple_choice", "prompt": "Why may male solitary bees emerge before females?", "options": ["They need to collect more pollen.", "They wait near nest entrances for females.", "They build all the nests for the colony.", "They protect the queen from predators."], "answer": "B", "explanation": "The passage says males often wait near nest entrances for females to appear."},
            {"type": "short_answer", "prompt": "Which type of bee uses pieces of leaves to line its nest?", "options": [], "answer": "leafcutter bee", "explanation": "Leafcutter bees cut pieces from leaves and use them to line their nests."},
            {"type": "tfng", "prompt": "All solitary bees build their nests underground.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "FALSE", "explanation": "Some nest in soil, but others use stems, walls, or dry wood."},
            {"type": "multiple_choice", "prompt": "Why can a small patch of bare soil be useful?", "options": ["Some bees dig their nests there.", "It produces honey without flowers.", "It keeps all insects away.", "It makes flowers bloom in winter."], "answer": "A", "explanation": "Mining bees dig tunnels in bare or lightly covered soil."},
            {"type": "short_answer", "prompt": "What do solitary bees move between flowers while collecting food?", "options": [], "answer": "pollen", "explanation": "The passage identifies solitary bees as important pollinators that move pollen between plants."},
            {"type": "multiple_choice", "prompt": "What kind of flowering season is useful for supporting different bee species?", "options": ["A very short season with one flower type", "A long season with flowers available at different times", "A season with flowers only in underground spaces", "A season with no native plants"], "answer": "B", "explanation": "Different species are active at different times, so a long flowering season helps them."},
            {"type": "tfng", "prompt": "Solitary bees defend a shared hive as a group.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "FALSE", "explanation": "Their defining feature is that each female builds and provisions her own nest."},
            {"type": "short_answer", "prompt": "What kind of garden chemical can harm bees directly?", "options": [], "answer": "pesticides", "explanation": "The passage warns that chemical pesticides can harm bees directly."},
            {"type": "multiple_choice", "prompt": "What do mason bees use to close their nest chambers?", "options": ["Mud", "Pollen only", "Tree bark", "Water"], "answer": "A", "explanation": "Mason bees use mud to close the chambers in a cavity."},
            {"type": "short_answer", "prompt": "What can a shallow dish with stones offer bees?", "options": [], "answer": "safe drinking place", "explanation": "The passage says a shallow dish of water with stones can offer a safe drinking place."},
            {"type": "multiple_choice", "prompt": "What is the best conclusion about supporting solitary bees?", "options": ["Only large farms can provide useful habitat.", "Small changes can provide meaningful habitat in city gardens.", "Solitary bees are less valuable than honey bees.", "Gardens should remove all old stems and bare soil."], "answer": "B", "explanation": "The final paragraph says small changes can provide a surprising amount of habitat."},
        ],
    },
]


LISTENING_SECTIONS = [
    {
        "title": "Section 1: Fernbridge Library Membership",
        "script": """Good morning. Welcome to Fernbridge Library. How can I help you today?\n\nHello. I have recently moved to Fernbridge and I would like to join the library. My name is Mina Rahman.\n\nWelcome, Ms Rahman. We offer several membership types. Because you live in the town and are over eighteen, you can apply for an adult resident membership. Visitors can also use the library, but their borrowing period is shorter.\n\nI would like the resident membership. What do I need to show?\n\nWe need one form of identification and proof of your local address. A passport is fine for identification, and a recent utility bill will prove your address. We can accept a digital bill on your phone.\n\nHow long will it take to receive the card?\n\nThe card will be ready for collection on Monday after three o'clock. You can use the reading room today, even before you collect it. Study room three is available on the second floor if you need a quiet place.\n\nIs there a locker nearby?\n\nYes. The lockers are on the second floor beside the study rooms. You can use a small locker without an additional charge, but please take your belongings before the library closes.\n\nDo you offer an introduction for new members?\n\nYes. The next orientation is on Saturday at ten in the morning, and it is free. During the orientation, a librarian will explain the online catalogue and the self-checkout machines.\n\nHow many books can I borrow?\n\nAn adult resident member can borrow eight books at one time. The standard borrowing period is three weeks. If you need help later, email library@fernbridge.org.\n\nThank you. I will bring my utility bill and return on Monday.""",
        "questions": [
            {"type": "short_answer", "prompt": "What is the visitor's surname?", "options": [], "answer": "Rahman", "explanation": "The visitor introduces herself as Mina Rahman."},
            {"type": "multiple_choice", "prompt": "Which membership does Mina choose?", "options": ["Child visitor", "Adult resident", "Short-term researcher", "International visitor"], "answer": "B", "explanation": "She chooses the adult resident membership because she lives in Fernbridge and is over eighteen."},
            {"type": "short_answer", "prompt": "What document can prove Mina's address?", "options": [], "answer": "utility bill", "explanation": "The librarian says a recent utility bill can prove her address."},
            {"type": "short_answer", "prompt": "On which day will Mina's library card be ready?", "options": [], "answer": "Monday", "explanation": "The card will be ready on Monday after three o'clock."},
            {"type": "short_answer", "prompt": "What is the number of the study room?", "options": [], "answer": "3", "explanation": "Study room three is available on the second floor."},
            {"type": "multiple_choice", "prompt": "Where are the lockers?", "options": ["In the basement", "Beside the entrance", "On the second floor", "Behind the café"], "answer": "C", "explanation": "The lockers are on the second floor beside the study rooms."},
            {"type": "tfng", "prompt": "The new-member orientation has an extra charge.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "FALSE", "explanation": "The librarian says the orientation is free."},
            {"type": "short_answer", "prompt": "What time is the orientation on Saturday?", "options": [], "answer": "10", "explanation": "The orientation starts at ten in the morning."},
            {"type": "short_answer", "prompt": "How many books can an adult resident borrow?", "options": [], "answer": "8", "explanation": "Adult resident members can borrow eight books at one time."},
            {"type": "short_answer", "prompt": "What is the library's email address?", "options": [], "answer": "library@fernbridge.org", "explanation": "The librarian gives library@fernbridge.org as the help email."},
        ],
    },
    {
        "title": "Section 2: WheelGo Bicycle Share",
        "script": """Good afternoon. This short presentation explains how to use the WheelGo bicycle-share service in Bellford. The service began in 2018 with twelve stations. It now has twenty-four stations across the town centre and the university district.\n\nTo borrow a bicycle, download the WheelGo app and create an account. The app shows the location of every station and the number of available bicycles. You can also use the blue membership card if you prefer not to use a phone.\n\nThe first thirty minutes of every journey are included in the basic membership. After that, the charge is one dollar and fifty cents for each additional half-hour. A journey can be ended only when the bicycle is returned to an empty docking space. Leaving a bicycle beside a station does not end the journey.\n\nThe service operates from six in the morning until eleven at night. It is not available during the overnight cleaning period. Helmets are not provided with the bicycles, so regular users should bring their own. The bicycles have front and rear lights, and a bell is fitted to every handlebar.\n\nIf you notice a problem, press the red button on the bicycle before returning it. The app will ask you to describe the fault. Do not try to repair the bicycle yourself. The maintenance team checks reported problems each morning.\n\nThe town plans to add four new stations on the north side next year. Residents can suggest exact locations through the transport department's website. The service is designed for short journeys, so people who need a bicycle for a whole day should use a normal rental shop instead.""",
        "questions": [
            {"type": "short_answer", "prompt": "In what year did the bicycle-share service begin?", "options": [], "answer": "2018", "explanation": "WheelGo began in 2018."},
            {"type": "short_answer", "prompt": "How many stations does the service have now?", "options": [], "answer": "24", "explanation": "The service now has twenty-four stations."},
            {"type": "short_answer", "prompt": "What is the name of the bicycle-share app?", "options": [], "answer": "WheelGo", "explanation": "Users can borrow a bicycle through the WheelGo app."},
            {"type": "multiple_choice", "prompt": "How long is included in the basic membership for each journey?", "options": ["15 minutes", "30 minutes", "45 minutes", "60 minutes"], "answer": "B", "explanation": "The first thirty minutes are included in the basic membership."},
            {"type": "short_answer", "prompt": "What is the charge for each additional half-hour?", "options": [], "answer": "1.50", "explanation": "Each additional half-hour costs one dollar and fifty cents."},
            {"type": "short_answer", "prompt": "What time does the service start each day?", "options": [], "answer": "6", "explanation": "The service operates from six in the morning."},
            {"type": "short_answer", "prompt": "What time does the service stop each night?", "options": [], "answer": "11", "explanation": "The service operates until eleven at night."},
            {"type": "tfng", "prompt": "A helmet is supplied with every WheelGo bicycle.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "FALSE", "explanation": "Helmets are not provided, so users should bring their own."},
            {"type": "short_answer", "prompt": "What colour is the button used to report a bicycle problem?", "options": [], "answer": "red", "explanation": "Users should press the red button before returning a bicycle with a problem."},
            {"type": "short_answer", "prompt": "On which side of town will four new stations be added?", "options": [], "answer": "north", "explanation": "The town plans to add four stations on the north side."},
        ],
    },
    {
        "title": "Section 3: Street Food Research Project",
        "script": """Dr Chen: So, Carlos and Leila, how is your research project developing?\n\nLeila: We have changed the focus slightly. At first we wanted to study what customers prefer to eat, but now we want to examine how independent street-food vendors adapt to changing customer habits.\n\nDr Chen: That is a clearer research question. Where will you collect your data?\n\nCarlos: At the Riverside Tuesday Market. It is large enough to give us different types of vendors, but it is small enough for us to observe the whole market. We plan to work with six vendors rather than every stall.\n\nDr Chen: What will you record during the observations?\n\nLeila: We will make fifteen-minute observations. We will record the length of the queue, changes to the menu, and the payment methods customers use. We will not record the total sales because vendors may consider that private information.\n\nCarlos: We also plan to interview each vendor for about twenty minutes. We will ask about changes they made during the past year, such as adding vegetarian dishes or accepting phone payments.\n\nDr Chen: Remember the ethics form.\n\nLeila: We have prepared it. Every vendor will give written consent before an interview. We may record audio, but only after permission. We will not film people's faces, and we will remove names from the report.\n\nDr Chen: How will you analyse the interviews?\n\nCarlos: We will code the answers into three main categories: convenience, price, and local ingredients. We will compare patterns between the Tuesday market and a weekend market, rather than compare individual cuisines.\n\nDr Chen: Good. When will you meet again?\n\nLeila: Next Wednesday at two in the afternoon. By then we should have completed the first round of observations.""",
        "questions": [
            {"type": "short_answer", "prompt": "What will the students study about street-food vendors?", "options": [], "answer": "adaptation", "explanation": "Their focus is how vendors adapt to changing customer habits."},
            {"type": "short_answer", "prompt": "What is the name of the market they will visit?", "options": [], "answer": "Riverside Tuesday Market", "explanation": "They will collect data at the Riverside Tuesday Market."},
            {"type": "short_answer", "prompt": "How many vendors will take part in the project?", "options": [], "answer": "6", "explanation": "The students plan to work with six vendors."},
            {"type": "short_answer", "prompt": "How long will each observation last?", "options": [], "answer": "15 minutes", "explanation": "The students will make fifteen-minute observations."},
            {"type": "multiple_choice", "prompt": "Which information will the students record?", "options": ["Total sales", "Queue length", "Vendor salaries", "Kitchen rent"], "answer": "B", "explanation": "Queue length is one of the observation measures."},
            {"type": "tfng", "prompt": "The students will film the faces of customers at the market.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "FALSE", "explanation": "They will not film people's faces."},
            {"type": "short_answer", "prompt": "How long will each vendor interview last?", "options": [], "answer": "20 minutes", "explanation": "Each interview will last about twenty minutes."},
            {"type": "multiple_choice", "prompt": "Which is one of the students' analysis categories?", "options": ["Weather", "Convenience", "Building height", "Tourism"], "answer": "B", "explanation": "The three categories are convenience, price, and local ingredients."},
            {"type": "tfng", "prompt": "The students will compare individual cuisines in their report.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "FALSE", "explanation": "They will compare patterns between markets rather than individual cuisines."},
            {"type": "short_answer", "prompt": "When is the students' next meeting?", "options": [], "answer": "next Wednesday at two", "explanation": "They will meet next Wednesday at two in the afternoon."},
        ],
    },
    {
        "title": "Section 4: Sleep and Memory",
        "script": """Today we will look at the relationship between sleep and memory. Learning is not finished when a class ends or when a person closes a textbook. During sleep, the brain reorganises some of the information it received during the day. Scientists call this process memory consolidation.\n\nOne structure involved in this process is the hippocampus. It acts like a temporary index for many new memories. Over time, the information can become more strongly connected with networks in the outer layer of the brain, known as the cortex. Sleep appears to help this transfer, although researchers are still studying the exact mechanism.\n\nSleep is not one uniform state. During non-REM sleep, especially the slow-wave stage, the brain produces large, slow patterns of activity. During REM sleep, brain activity is more similar to waking activity and dreaming is common. A typical sleep cycle lasts about ninety minutes, and people move through several cycles during a night.\n\nIn one study, volunteers learned thirty new vocabulary words in the evening. Half of them were tested immediately and again the next morning after a normal night of sleep. The other half stayed awake for the same period. The group that slept remembered more words, especially when the learning session had been followed by a quiet period rather than a distracting activity.\n\nResearchers think that the sleeping brain may replay recent patterns of activity. This replay can strengthen useful connections and weaken details that are not important. Sleep does not simply store every piece of information equally. It helps the brain organise learning and connect it with knowledge already held.\n\nPractical habits also matter. Caffeine taken within six hours of bedtime can reduce sleep quality for some people. A regular schedule, a dark room, and a slightly cool temperature can make sleep easier. A short nap of about twenty minutes may improve alertness, but a long nap late in the day can make it harder to sleep at night.\n\nThe main message is not that sleep replaces study. People still need to pay attention and practise. Sleep gives the brain time to process that work, so protecting sleep is one of the simplest ways to support learning.""",
        "questions": [
            {"type": "short_answer", "prompt": "What is the process of reorganising information during sleep called?", "options": [], "answer": "memory consolidation", "explanation": "The lecture names this process memory consolidation."},
            {"type": "short_answer", "prompt": "Which brain structure acts as a temporary index for new memories?", "options": [], "answer": "hippocampus", "explanation": "The hippocampus acts like a temporary index for many new memories."},
            {"type": "multiple_choice", "prompt": "Which stage is associated with large, slow patterns of brain activity?", "options": ["REM sleep", "Slow-wave non-REM sleep", "The waking stage", "The dreaming stage only"], "answer": "B", "explanation": "Slow-wave non-REM sleep produces large, slow patterns of activity."},
            {"type": "short_answer", "prompt": "About how long does a typical sleep cycle last?", "options": [], "answer": "90 minutes", "explanation": "A typical sleep cycle lasts about ninety minutes."},
            {"type": "short_answer", "prompt": "How many vocabulary words did volunteers learn in the study?", "options": [], "answer": "30", "explanation": "The volunteers learned thirty new vocabulary words."},
            {"type": "multiple_choice", "prompt": "What may replay during sleep?", "options": ["Recent patterns of brain activity", "Only sounds from the bedroom", "Every conversation from childhood", "The movement of the body"], "answer": "A", "explanation": "Researchers think the sleeping brain may replay recent patterns of activity."},
            {"type": "short_answer", "prompt": "Within how many hours of bedtime can caffeine reduce sleep quality?", "options": [], "answer": "6 hours", "explanation": "Caffeine taken within six hours of bedtime may reduce sleep quality."},
            {"type": "multiple_choice", "prompt": "Which room condition can support better sleep?", "options": ["A bright and hot room", "A dark and slightly cool room", "A noisy room with changing temperature", "A room with strong perfume"], "answer": "B", "explanation": "The lecture recommends a regular schedule, a dark room, and a slightly cool temperature."},
            {"type": "short_answer", "prompt": "How long should a short nap be?", "options": [], "answer": "20 minutes", "explanation": "A short nap of about twenty minutes may improve alertness."},
            {"type": "tfng", "prompt": "The lecture says sleep can replace attention and practice when learning.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "FALSE", "explanation": "The conclusion says people still need to pay attention and practise."},
        ],
    },
]


# These compact source records generate nine additional original full-length
# mocks. They keep the seed file maintainable while still giving every mock
# different passages, scripts, facts, and answer keys.
ADDITIONAL_READING_MOCKS = [
    {
        "title": "Reading Mock 2: Community Energy",
        "passages": [
            {"title": "Solar Co-operatives on Hillsides", "setting": "the hillside town of Narin", "year": "2016", "quantity": "18 rooftops", "method": "monthly energy audits", "benefit": "lower electricity bills for participating households", "challenge": "different roofs receive different amounts of sunlight", "outcome": "members began sharing power during winter", "monitor": "kilowatt-hours generated each month"},
            {"title": "The Battery Library", "setting": "a housing district beside the old railway", "year": "2020", "quantity": "120 battery packs", "method": "barcode checkouts", "benefit": "fewer households need to buy tools for occasional jobs", "challenge": "packs must be returned charged", "outcome": "the library served more repair groups than expected", "monitor": "the number of successful returns"},
            {"title": "A Small Wind Project", "setting": "the farming valley of Eren", "year": "2018", "quantity": "six turbines", "method": "seasonal wind measurements", "benefit": "the pumping station uses less diesel", "challenge": "winter storms can stop maintenance work", "outcome": "the farmers formed a shared maintenance team", "monitor": "turbine output after storms"},
        ],
    },
    {
        "title": "Reading Mock 3: Food and Science",
        "passages": [
            {"title": "Farms Above the Market", "setting": "the roof of a covered market in Luma", "year": "2014", "quantity": "900 square metres", "method": "lightweight planting beds", "benefit": "fresh herbs travel a shorter distance to local kitchens", "challenge": "the roof can become very hot in summer", "outcome": "the market installed shade cloths and collected more rainwater", "monitor": "plant survival during heat waves"},
            {"title": "The Town Seed Bank", "setting": "the public library of Westbridge", "year": "2009", "quantity": "350 local seed varieties", "method": "annual germination tests", "benefit": "gardeners can grow plants suited to the local climate", "challenge": "seeds lose quality if storage is too humid", "outcome": "school gardens began growing older varieties", "monitor": "germination rates each spring"},
            {"title": "Learning from Fermentation", "setting": "a food laboratory near the harbour", "year": "2021", "quantity": "24 starter cultures", "method": "temperature-controlled trials", "benefit": "small producers can improve flavour without expensive equipment", "challenge": "a culture can change when conditions vary", "outcome": "the lab published a simple safety guide", "monitor": "acidity levels during each trial"},
        ],
    },
    {
        "title": "Reading Mock 4: Learning in Public",
        "passages": [
            {"title": "Walking Classrooms", "setting": "the historic centre of Bellford", "year": "2017", "quantity": "ten weekly routes", "method": "short lessons at marked stops", "benefit": "students connect geography with everyday places", "challenge": "rain can interrupt the outdoor schedule", "outcome": "teachers created indoor map activities for wet days", "monitor": "student attendance on each route"},
            {"title": "Signs in Two Languages", "setting": "the multilingual neighbourhood of Darya", "year": "2013", "quantity": "64 street signs", "method": "resident language surveys", "benefit": "new arrivals can find public services more easily", "challenge": "long translations do not fit on small signs", "outcome": "the council adopted shorter shared symbols", "monitor": "requests for directions at service centres"},
            {"title": "Peer Mentors at Night", "setting": "a community college in Southport", "year": "2019", "quantity": "42 volunteer mentors", "method": "weekly study circles", "benefit": "adult learners receive help outside class hours", "challenge": "volunteers have different levels of experience", "outcome": "the college added mentor training sessions", "monitor": "completed assignments each term"},
        ],
    },
    {
        "title": "Reading Mock 5: Living with the Coast",
        "passages": [
            {"title": "Mangroves and Storm Water", "setting": "the eastern shoreline of Kawa", "year": "2012", "quantity": "14 hectares", "method": "planting locally collected seedlings", "benefit": "wave energy is reduced before it reaches homes", "challenge": "young plants are damaged by grazing animals", "outcome": "farmers built simple protective fences", "monitor": "seedling survival after high tides"},
            {"title": "Gardens That Float", "setting": "a lake village in Maru", "year": "2015", "quantity": "30 floating gardens", "method": "woven reed platforms", "benefit": "families can grow vegetables during seasonal floods", "challenge": "platforms drift when the wind is strong", "outcome": "the village added shared anchor points", "monitor": "vegetable harvests during flood months"},
            {"title": "Holding Sand on the Dunes", "setting": "the beach town of Orin", "year": "2008", "quantity": "five kilometres of dunes", "method": "wooden fences and native grasses", "benefit": "sand remains in place beside the main road", "challenge": "visitors create gaps by taking direct paths", "outcome": "the town marked raised walking routes", "monitor": "the height of the dune line"},
        ],
    },
    {
        "title": "Reading Mock 6: Materials with a Second Life",
        "passages": [
            {"title": "Tiles from Recycled Glass", "setting": "a small factory outside Merin", "year": "2011", "quantity": "three tonnes of glass each week", "method": "colour sorting before crushing", "benefit": "old bottles become durable building tiles", "challenge": "mixed glass colours are difficult to separate", "outcome": "the factory introduced collection bins by colour", "monitor": "the percentage of glass reused"},
            {"title": "Bamboo for Local Buildings", "setting": "the warm highlands of Sola", "year": "2016", "quantity": "seven demonstration homes", "method": "seasoning poles before construction", "benefit": "builders use a fast-growing local material", "challenge": "unseasoned bamboo can attract insects", "outcome": "a training course became part of the building programme", "monitor": "moisture levels in stored poles"},
            {"title": "Furniture in Modules", "setting": "a design studio in Northport", "year": "2022", "quantity": "nine standard components", "method": "reversible joints and replaceable panels", "benefit": "owners can repair one part instead of replacing a whole item", "challenge": "customers initially found the system unfamiliar", "outcome": "the studio opened a public repair desk", "monitor": "the number of parts replaced"},
        ],
    },
    {
        "title": "Reading Mock 7: Designing a Healthier Town",
        "passages": [
            {"title": "Cool Roofs for Hot Streets", "setting": "the apartment blocks of Jalen", "year": "2018", "quantity": "27 buildings", "method": "reflective roof coatings", "benefit": "top-floor rooms stay cooler in summer", "challenge": "coatings need renewal after several years", "outcome": "building managers created a shared maintenance fund", "monitor": "indoor temperatures during heat alerts"},
            {"title": "The Clinic on Wheels", "setting": "villages along the northern road", "year": "2010", "quantity": "four mobile clinics", "method": "a rotating weekly timetable", "benefit": "patients can receive basic checks closer to home", "challenge": "rough roads delay the timetable", "outcome": "the service added a second route for winter", "monitor": "missed appointments each month"},
            {"title": "Quiet Parks", "setting": "three busy neighbourhoods in Riva", "year": "2019", "quantity": "nine quiet zones", "method": "planting belts beside walking paths", "benefit": "people have calmer places to rest outdoors", "challenge": "traffic noise remains high at the boundaries", "outcome": "the city added low walls and water features", "monitor": "recorded sound levels at midday"},
        ],
    },
    {
        "title": "Reading Mock 8: Water in Unexpected Places",
        "passages": [
            {"title": "Rain Gardens by the School", "setting": "the school district of Arno", "year": "2015", "quantity": "22 rain gardens", "method": "shallow planted depressions", "benefit": "heavy rain reaches drains more slowly", "challenge": "children can compact the soil during play", "outcome": "the gardens were surrounded by low paths", "monitor": "the time needed for water to disappear"},
            {"title": "Nets That Catch Fog", "setting": "the dry ridge of Pelan", "year": "2007", "quantity": "80 mesh panels", "method": "vertical collection nets", "benefit": "villagers receive extra water during dry months", "challenge": "dust blocks the mesh after long winds", "outcome": "volunteers began cleaning panels every week", "monitor": "litres collected overnight"},
            {"title": "Mapping the Hidden Aquifer", "setting": "the agricultural plain of Varo", "year": "2020", "quantity": "48 monitoring wells", "method": "seasonal groundwater readings", "benefit": "farmers can plan irrigation without over-pumping", "challenge": "readings change after unusually wet seasons", "outcome": "the water authority published a shared map", "monitor": "the depth of the water table"},
        ],
    },
    {
        "title": "Reading Mock 9: Memory, Media, and Place",
        "passages": [
            {"title": "A Digital Archive for Families", "setting": "the former textile district of Noma", "year": "2014", "quantity": "2,600 recorded interviews", "method": "community scanning days", "benefit": "residents can preserve photographs and stories", "challenge": "some old formats are difficult to read", "outcome": "a repair group restored several tape machines", "monitor": "the number of items with complete descriptions"},
            {"title": "The Community Radio Hour", "setting": "the mountain town of Tesa", "year": "2005", "quantity": "two weekly programmes", "method": "listener questions and local reports", "benefit": "isolated residents receive useful local information", "challenge": "storms sometimes interrupt the signal", "outcome": "the station installed a backup transmitter", "monitor": "messages received from remote villages"},
            {"title": "Maps Made by Neighbours", "setting": "the riverside quarter of Ledo", "year": "2018", "quantity": "11 public maps", "method": "walking surveys with residents", "benefit": "planners can see paths missing from official maps", "challenge": "different groups remember street names differently", "outcome": "the project added pronunciation notes", "monitor": "map corrections submitted each season"},
        ],
    },
    {
        "title": "Reading Mock 10: Moving People and Goods",
        "passages": [
            {"title": "Cargo Bikes in the Centre", "setting": "the narrow streets of Old Harun", "year": "2017", "quantity": "35 electric cargo bikes", "method": "shared delivery hubs", "benefit": "small shops receive goods without large vans", "challenge": "batteries need charging after long routes", "outcome": "the hubs added solar charging roofs", "monitor": "deliveries completed before noon"},
            {"title": "The Night Train Experiment", "setting": "the rail corridor between Vesta and Kori", "year": "2021", "quantity": "four weekly services", "method": "reserved sleeping compartments", "benefit": "travellers can arrive without losing a working day", "challenge": "track maintenance limits the timetable", "outcome": "the railway published maintenance dates early", "monitor": "occupancy on each service"},
            {"title": "A Street without Cars", "setting": "the central avenue of Pera", "year": "2013", "quantity": "1.2 kilometres of road", "method": "morning delivery windows", "benefit": "pedestrians have a safer route through the centre", "challenge": "businesses need reliable delivery times", "outcome": "shops agreed on a shared delivery schedule", "monitor": "pedestrian counts on market days"},
        ],
    },
]


ADDITIONAL_LISTENING_MOCKS = [
    {
        "title": "Listening Mock 2: Community Energy Meetings", "theme": "a community energy programme", "sections": [
            {"title": "Section 1: Meter Appointment", "person": "Nadia Karim", "place": "Maple Court", "date": "Tuesday", "time": "9:30", "quantity": "two meters", "item": "a recent electricity bill", "purpose": "arrange a home energy check", "outcome": "receive a text confirmation"},
            {"title": "Section 2: Solar Workshop", "person": "Owen Price", "place": "the Green Hall", "date": "Saturday", "time": "11:00", "quantity": "14 panels", "item": "a notebook", "purpose": "learn how rooftop panels are maintained", "outcome": "take home a maintenance checklist"},
            {"title": "Section 3: Council Presentation", "person": "Mara Singh", "place": "the civic chamber", "date": "Thursday", "time": "18:00", "quantity": "five proposals", "item": "a printed map", "purpose": "present neighbourhood energy plans", "outcome": "collect questions from residents"},
            {"title": "Section 4: Wind Power Lecture", "person": "Dr Elias Noor", "place": "the technical college", "date": "Monday", "time": "14:15", "quantity": "three case studies", "item": "a calculator", "purpose": "compare small wind turbines", "outcome": "complete a short energy estimate"},
        ]},
    {
        "title": "Listening Mock 3: Food and Farming", "theme": "local food and farming projects", "sections": [
            {"title": "Section 1: Farm Visit", "person": "Lina Costa", "place": "Riverbend Farm", "date": "Wednesday", "time": "08:00", "quantity": "six visitors", "item": "closed shoes", "purpose": "book a guided farm visit", "outcome": "meet beside the tool shed"},
            {"title": "Section 2: Market Talk", "person": "Jon Bell", "place": "the central market", "date": "Friday", "time": "17:30", "quantity": "four food stalls", "item": "a reusable bag", "purpose": "explain the seasonal produce scheme", "outcome": "answer questions at the information table"},
            {"title": "Section 3: Student Research", "person": "Aisha Rahim", "place": "the university kitchen", "date": "Tuesday", "time": "13:00", "quantity": "eight recipes", "item": "a voice recorder", "purpose": "study traditional preservation methods", "outcome": "share a draft report"},
            {"title": "Section 4: Soil Lecture", "person": "Professor Marko Lee", "place": "the agriculture institute", "date": "Thursday", "time": "10:45", "quantity": "four soil types", "item": "a hand lens", "purpose": "identify healthy soil structure", "outcome": "label samples for the next class"},
        ]},
    {
        "title": "Listening Mock 4: Learning in Public", "theme": "new learning opportunities in a town", "sections": [
            {"title": "Section 1: Evening Course", "person": "Sara Mills", "place": "Westbridge College", "date": "Monday", "time": "19:00", "quantity": "eight lessons", "item": "a passport photograph", "purpose": "enrol in a language course", "outcome": "collect a student card"},
            {"title": "Section 2: Museum Walk", "person": "Peter Young", "place": "the old harbour museum", "date": "Sunday", "time": "15:00", "quantity": "three galleries", "item": "comfortable shoes", "purpose": "introduce a history walking route", "outcome": "finish beside the lighthouse"},
            {"title": "Section 3: Mentor Meeting", "person": "Noor Patel", "place": "the learning centre", "date": "Wednesday", "time": "16:20", "quantity": "ten mentors", "item": "a draft timetable", "purpose": "organise peer study groups", "outcome": "send the final list by email"},
            {"title": "Section 4: Memory Lecture", "person": "Dr Hana Cole", "place": "the public auditorium", "date": "Friday", "time": "12:30", "quantity": "two experiments", "item": "a question card", "purpose": "explain how practice supports memory", "outcome": "try a recall exercise"},
        ]},
    {
        "title": "Listening Mock 5: Living with the Coast", "theme": "coastal protection and community work", "sections": [
            {"title": "Section 1: Beach Survey", "person": "Tom Avery", "place": "Kawa shoreline", "date": "Tuesday", "time": "07:15", "quantity": "nine volunteers", "item": "a sun hat", "purpose": "join a shoreline survey", "outcome": "meet at the blue gate"},
            {"title": "Section 2: Dune Advice", "person": "Rita Sol", "place": "Orin visitor centre", "date": "Saturday", "time": "10:30", "quantity": "five walking routes", "item": "a water bottle", "purpose": "learn how to protect the dunes", "outcome": "receive a printed route map"},
            {"title": "Section 3: Fishermen's Interview", "person": "Leo Martins", "place": "the harbour office", "date": "Thursday", "time": "15:40", "quantity": "seven interviews", "item": "consent forms", "purpose": "record changes in local fishing", "outcome": "store recordings in a secure folder"},
            {"title": "Section 4: Wetland Lecture", "person": "Dr Mira Chen", "place": "the marine centre", "date": "Monday", "time": "09:50", "quantity": "three wetland types", "item": "field notes", "purpose": "compare habitats along the coast", "outcome": "draw a simple habitat diagram"},
        ]},
    {
        "title": "Listening Mock 6: Materials with a Second Life", "theme": "materials that can be reused", "sections": [
            {"title": "Section 1: Repair Desk", "person": "Milan Ortiz", "place": "Northport design studio", "date": "Thursday", "time": "10:00", "quantity": "one broken chair", "item": "a photograph of the joint", "purpose": "book a furniture repair", "outcome": "receive a price estimate"},
            {"title": "Section 2: Glass Factory Tour", "person": "Ella Green", "place": "Merin glass works", "date": "Friday", "time": "14:00", "quantity": "three safety zones", "item": "protective glasses", "purpose": "see how bottles become tiles", "outcome": "watch the crushing machine"},
            {"title": "Section 3: Builder Discussion", "person": "Kofi Mensah", "place": "the bamboo workshop", "date": "Wednesday", "time": "11:45", "quantity": "seven sample poles", "item": "a moisture meter", "purpose": "choose materials for a small house", "outcome": "compare the sample walls"},
            {"title": "Section 4: Design Lecture", "person": "Lara White", "place": "the industrial design school", "date": "Tuesday", "time": "16:00", "quantity": "nine components", "item": "a sketchbook", "purpose": "introduce modular furniture", "outcome": "design a replaceable panel"},
        ]},
    {
        "title": "Listening Mock 7: Designing a Healthier Town", "theme": "health and comfort in urban spaces", "sections": [
            {"title": "Section 1: Clinic Booking", "person": "Amir Das", "place": "the mobile clinic", "date": "Monday", "time": "08:45", "quantity": "two health checks", "item": "a health card", "purpose": "arrange a basic health appointment", "outcome": "wait near the community hall"},
            {"title": "Section 2: Park Tour", "person": "Helen Ward", "place": "Riva quiet park", "date": "Sunday", "time": "09:30", "quantity": "nine quiet zones", "item": "a small umbrella", "purpose": "show new park features", "outcome": "finish at the water garden"},
            {"title": "Section 3: Roof Project", "person": "Dani Iqbal", "place": "Jalen apartment block", "date": "Saturday", "time": "12:10", "quantity": "27 roofs", "item": "a building plan", "purpose": "evaluate a cooling roof project", "outcome": "write a report for managers"},
            {"title": "Section 4: Heat Lecture", "person": "Professor Ruth Hall", "place": "the public health centre", "date": "Thursday", "time": "17:00", "quantity": "four risk groups", "item": "a temperature chart", "purpose": "explain heat safety", "outcome": "prepare an advice poster"},
        ]},
    {
        "title": "Listening Mock 8: Water in Unexpected Places", "theme": "water collection and protection", "sections": [
            {"title": "Section 1: Garden Registration", "person": "Ivo Marin", "place": "Arno school district", "date": "Tuesday", "time": "16:30", "quantity": "22 gardens", "item": "a garden plan", "purpose": "join a rain-garden project", "outcome": "receive a planting guide"},
            {"title": "Section 2: Fog Net Visit", "person": "Maya Osei", "place": "the Pelan ridge", "date": "Wednesday", "time": "06:20", "quantity": "80 panels", "item": "a warm jacket", "purpose": "inspect water-collection nets", "outcome": "measure the morning harvest"},
            {"title": "Section 3: Well Survey", "person": "Ken Ito", "place": "the Varo water office", "date": "Friday", "time": "13:15", "quantity": "48 wells", "item": "a site map", "purpose": "plan groundwater readings", "outcome": "upload data to the shared map"},
            {"title": "Section 4: Aquifer Lecture", "person": "Dr Selma Farah", "place": "the regional university", "date": "Monday", "time": "11:00", "quantity": "three water layers", "item": "a clear ruler", "purpose": "understand underground water movement", "outcome": "complete a cross-section drawing"},
        ]},
    {
        "title": "Listening Mock 9: Memory, Media, and Place", "theme": "how communities preserve local memory", "sections": [
            {"title": "Section 1: Archive Appointment", "person": "Nora Bell", "place": "the Noma archive", "date": "Wednesday", "time": "10:15", "quantity": "six photographs", "item": "an identity card", "purpose": "digitise family photographs", "outcome": "collect the files next week"},
            {"title": "Section 2: Radio Programme", "person": "Omar Field", "place": "the Tesa radio station", "date": "Friday", "time": "18:30", "quantity": "two programmes", "item": "a list of questions", "purpose": "volunteer for a local radio hour", "outcome": "read a community announcement"},
            {"title": "Section 3: Map Workshop", "person": "Yuki Tan", "place": "the Ledo neighbourhood hall", "date": "Saturday", "time": "14:45", "quantity": "11 maps", "item": "comfortable walking shoes", "purpose": "add local paths to a map", "outcome": "compare notes with neighbours"},
            {"title": "Section 4: Oral History Lecture", "person": "Dr Samuel Reed", "place": "the city museum", "date": "Tuesday", "time": "15:00", "quantity": "three interview stages", "item": "a consent form", "purpose": "explain ethical oral history", "outcome": "draft an interview opening"},
        ]},
    {
        "title": "Listening Mock 10: Moving People and Goods", "theme": "transport choices for growing towns", "sections": [
            {"title": "Section 1: Cargo Delivery", "person": "Rafi Khan", "place": "the Old Harun delivery hub", "date": "Monday", "time": "06:45", "quantity": "35 cargo bikes", "item": "a driver licence", "purpose": "register for a delivery route", "outcome": "collect a charging key"},
            {"title": "Section 2: Night Train Booking", "person": "Clara Moss", "place": "the Vesta ticket office", "date": "Thursday", "time": "20:00", "quantity": "four weekly trains", "item": "a passport", "purpose": "book a sleeping compartment", "outcome": "receive an electronic ticket"},
            {"title": "Section 3: Avenue Consultation", "person": "Beni Costa", "place": "the Pera town hall", "date": "Tuesday", "time": "17:15", "quantity": "1.2 kilometres", "item": "a shop timetable", "purpose": "discuss a car-free avenue", "outcome": "agree on delivery hours"},
            {"title": "Section 4: Transport Lecture", "person": "Professor Lina Fox", "place": "the mobility institute", "date": "Wednesday", "time": "09:00", "quantity": "three transport modes", "item": "a route diagram", "purpose": "compare urban transport systems", "outcome": "calculate a journey time"},
        ]},
]


def _generated_reading_body(passage):
    return f"""{passage['title']}\n\nIn {passage['setting']}, a local project began in {passage['year']} after residents noticed that ordinary systems were not meeting every need. The first stage involved {passage['quantity']}. Rather than relying on a single large solution, the organisers worked with residents and tested a practical method: {passage['method']}.\n\nThe project was designed to produce a clear local benefit. In its early reports, the most frequently mentioned benefit was {passage['benefit']}. People could see the change in everyday life, although the organisers warned that the project was not effortless. Its main challenge was that {passage['challenge']}.\n\nTo improve the design, the team recorded results and adjusted the programme. By the end of the first phase, {passage['outcome']}. The team also encouraged residents to ask questions and suggest changes, because local knowledge often revealed problems that a plan on paper could miss.\n\nThe project is still evaluated rather than treated as finished. Coordinators monitor {passage['monitor']} and compare the results with earlier records. Their experience suggests that useful public projects depend on simple measurements, cooperation, and a willingness to improve a design after people begin using it."""


def _generated_reading_questions(passage, include_extra=False):
    return [
        {"type": "multiple_choice", "prompt": "What is the main purpose of this passage?", "options": ["To list unrelated historical dates", "To describe a local project, its benefits, and its challenges", "To argue that local projects are unnecessary", "To compare two international companies"], "answer": "B", "explanation": "The passage describes the project, its method, benefit, challenge, and evaluation."},
        {"type": "tfng", "prompt": f"The project began before {passage['year']}.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "FALSE", "explanation": f"The passage states that the project began in {passage['year']}."},
        {"type": "short_answer", "prompt": "In what year did the project begin?", "options": [], "answer": passage["year"], "explanation": f"The project began in {passage['year']}."},
        {"type": "multiple_choice", "prompt": "Which method did the organisers use?", "options": [passage["method"], "A national advertising campaign", "A private membership scheme", "A yearly competition"], "answer": "A", "explanation": f"The passage identifies {passage['method']} as the practical method used."},
        {"type": "short_answer", "prompt": "What quantity was involved in the first stage?", "options": [], "answer": passage["quantity"], "explanation": f"The first stage involved {passage['quantity']}."},
        {"type": "tfng", "prompt": "The passage says the project had no challenges.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "FALSE", "explanation": f"The main challenge was that {passage['challenge']}."},
        {"type": "multiple_choice", "prompt": "What benefit did the project aim to provide?", "options": ["A larger private office", "Faster international travel", passage["benefit"], "Fewer public measurements"], "answer": "C", "explanation": f"The passage identifies {passage['benefit']} as the main benefit."},
        {"type": "short_answer", "prompt": "What was the main challenge?", "options": [], "answer": passage["challenge"], "explanation": f"The passage states that the main challenge was {passage['challenge']}."},
        {"type": "tfng", "prompt": "The passage says that every resident supported the project from the start.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "NOT GIVEN", "explanation": "The passage mentions cooperation and questions but does not say every resident supported the project."},
        {"type": "short_answer", "prompt": "Where was the project carried out?", "options": [], "answer": passage["setting"], "explanation": f"The project took place in {passage['setting']}."},
        {"type": "multiple_choice", "prompt": "What happened by the end of the first phase?", "options": [passage["outcome"], "The project was cancelled immediately", "All measurements were removed", "The organisers moved overseas"], "answer": "A", "explanation": f"The passage reports that {passage['outcome']}."},
        {"type": "tfng", "prompt": "The project was designed only for specialists.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "FALSE", "explanation": "The passage describes cooperation with residents and local knowledge."},
        {"type": "multiple_choice", "prompt": "What does the passage suggest about successful public projects?", "options": ["They need measurement, cooperation, and improvement.", "They should never change after launch.", "They work only in large cities.", "They should avoid residents' opinions."], "answer": "A", "explanation": "The final sentence highlights simple measurements, cooperation, and willingness to improve."},
    ] + ([{"type": "short_answer", "prompt": "What do coordinators monitor?", "options": [], "answer": passage["monitor"], "explanation": f"Coordinators monitor {passage['monitor']}."}] if include_extra else [])


def _speaker_first_name(person):
    parts = person.split()
    if parts[0].rstrip(".") in {"Dr", "Professor"} and len(parts) > 1:
        return parts[1]
    return parts[0]


def _generated_listening_script(section, theme):
    email = f"{_speaker_first_name(section['person']).lower()}@practice.example.com"
    return f"""Welcome to this information session about {theme}. Today we are focusing on {section['title'].lower()}.\n\nMy name is {section['person']}, and I will meet participants at {section['place']}. The activity is scheduled for {section['date']} at {section['time']}. Please note that the group will include {section['quantity']}, so arrive a few minutes early.\n\nThe purpose of the activity is to {section['purpose']}. Participants should bring {section['item']}. No special payment is required, but everyone must follow the organiser's safety instructions. If the weather or timetable changes, an update will be sent before the activity.\n\nAt the end, participants will {section['outcome']}. For questions, email {email} before the group leaves the meeting point."""


def _generated_listening_questions(section):
    first_name = _speaker_first_name(section["person"])
    email = f"{first_name.lower()}@practice.example.com"
    return [
        {"type": "short_answer", "prompt": "What is the organiser's first name?", "options": [], "answer": first_name, "explanation": f"The organiser introduces themselves as {section['person']}."},
        {"type": "multiple_choice", "prompt": "What is the main purpose of the activity?", "options": ["To cancel a public service", section["purpose"], "To sell train tickets", "To recruit professional actors"], "answer": "B", "explanation": f"The purpose is to {section['purpose']}."},
        {"type": "short_answer", "prompt": "Where will participants meet?", "options": [], "answer": section["place"], "explanation": f"Participants meet at {section['place']}."},
        {"type": "short_answer", "prompt": "On which day will the activity take place?", "options": [], "answer": section["date"], "explanation": f"The activity is scheduled for {section['date']}."},
        {"type": "short_answer", "prompt": "What time will the activity begin?", "options": [], "answer": section["time"], "explanation": f"The activity begins at {section['time']}."},
        {"type": "short_answer", "prompt": "What number or quantity is mentioned for the group or activity?", "options": [], "answer": section["quantity"], "explanation": f"The speaker mentions {section['quantity']}."},
        {"type": "multiple_choice", "prompt": "What should participants bring?", "options": ["A passport", "A camera", section["item"], "A musical instrument"], "answer": "C", "explanation": f"Participants should bring {section['item']}."},
        {"type": "tfng", "prompt": "Participants must pay a special fee before joining.", "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "FALSE", "explanation": "The script says no special payment is required."},
        {"type": "short_answer", "prompt": "What is the organiser's first-name email address?", "options": [], "answer": email, "explanation": f"The practice contact address is {email}."},
        {"type": "multiple_choice", "prompt": "What will happen at the end?", "options": [section["outcome"], "The activity will move to another country", "All records will be deleted", "Participants will receive a driving licence"], "answer": "A", "explanation": f"At the end, participants will {section['outcome']}."},
    ]


LEGACY_DEMO_TITLES = (
    "Reading Mock 1: The Repair Café Movement",
    "Listening Mock 1: Community Garden Orientation",
)


def _create_or_reset_mock(db, skill, title, description, time_limit, expected_questions):
    existing = db.execute(
        "SELECT id FROM mock_tests WHERE title = ?", (title,)
    ).fetchone()
    if existing:
        count = db.execute(
            "SELECT COUNT(*) AS count FROM questions WHERE mock_id = ?",
            (existing["id"],),
        ).fetchone()["count"]
        if count == expected_questions:
            return existing["id"]

        # Upgrade only these demo mocks; user accounts and other content remain untouched.
        db.execute("DELETE FROM attempts WHERE mock_id = ?", (existing["id"],))
        db.execute("DELETE FROM mock_tests WHERE id = ?", (existing["id"],))

    cursor = db.execute(
        """
        INSERT INTO mock_tests (skill, title, description, time_limit_minutes, is_published)
        VALUES (?, ?, ?, ?, 1)
        """,
        (skill, title, description, time_limit),
    )
    return cursor.lastrowid


def _create_questions(db, mock_id, questions, start_number=1, **parent):
    for offset, question in enumerate(questions):
        db.execute(
            """
            INSERT INTO questions (
                mock_id, passage_id, listening_script_id, question_number,
                question_type, prompt, options_json, correct_answer, explanation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mock_id,
                parent.get("passage_id"),
                parent.get("listening_script_id"),
                start_number + offset,
                question["type"],
                question["prompt"],
                json.dumps(question["options"]),
                question["answer"],
                question["explanation"],
            ),
        )


def seed_demo_content():
    db = get_db()

    for legacy_title in LEGACY_DEMO_TITLES:
        legacy = db.execute(
            "SELECT id FROM mock_tests WHERE title = ?", (legacy_title,)
        ).fetchone()
        if legacy:
            db.execute("DELETE FROM attempts WHERE mock_id = ?", (legacy["id"],))
            db.execute("DELETE FROM mock_tests WHERE id = ?", (legacy["id"],))

    reading_id = _create_or_reset_mock(
        db,
        "reading",
        "Reading Mock 1: The Hidden Life of Urban Trees",
        "Full-length original Reading practice: three passages and forty questions.",
        60,
        40,
    )
    if db.execute(
        "SELECT COUNT(*) AS count FROM questions WHERE mock_id = ?", (reading_id,)
    ).fetchone()["count"] == 0:
        question_number = 1
        for passage in READING_PASSAGES:
            cursor = db.execute(
                """
                INSERT INTO reading_passages (mock_id, title, body, display_order)
                VALUES (?, ?, ?, ?)
                """,
                (reading_id, passage["title"], passage["body"], question_number),
            )
            _create_questions(
                db,
                reading_id,
                passage["questions"],
                start_number=question_number,
                passage_id=cursor.lastrowid,
            )
            question_number += len(passage["questions"])

    listening_id = _create_or_reset_mock(
        db,
        "listening",
        "Listening Mock 1: Full Practice Test",
        "Full-length original Listening practice: four sections and forty questions.",
        40,
        40,
    )
    if db.execute(
        "SELECT COUNT(*) AS count FROM questions WHERE mock_id = ?", (listening_id,)
    ).fetchone()["count"] == 0:
        question_number = 1
        for section in LISTENING_SECTIONS:
            cursor = db.execute(
                """
                INSERT INTO listening_scripts (mock_id, title, script, display_order)
                VALUES (?, ?, ?, ?)
                """,
                (listening_id, section["title"], section["script"], question_number),
            )
            _create_questions(
                db,
                listening_id,
                section["questions"],
                start_number=question_number,
                listening_script_id=cursor.lastrowid,
            )
            question_number += len(section["questions"])

    for pack in ADDITIONAL_READING_MOCKS:
        mock_id = _create_or_reset_mock(
            db,
            "reading",
            pack["title"],
            "Full-length original Reading practice: three passages and forty questions.",
            60,
            40,
        )
        if db.execute(
            "SELECT COUNT(*) AS count FROM questions WHERE mock_id = ?", (mock_id,)
        ).fetchone()["count"] == 0:
            question_number = 1
            for passage_index, passage in enumerate(pack["passages"], start=1):
                passage_body = _generated_reading_body(passage)
                cursor = db.execute(
                    """
                    INSERT INTO reading_passages (mock_id, title, body, display_order)
                    VALUES (?, ?, ?, ?)
                    """,
                    (mock_id, passage["title"], passage_body, passage_index),
                )
                passage_questions = _generated_reading_questions(
                    passage, include_extra=passage_index == 3
                )
                _create_questions(
                    db,
                    mock_id,
                    passage_questions,
                    start_number=question_number,
                    passage_id=cursor.lastrowid,
                )
                question_number += len(passage_questions)

    for pack in ADDITIONAL_LISTENING_MOCKS:
        mock_id = _create_or_reset_mock(
            db,
            "listening",
            pack["title"],
            "Full-length original Listening practice: four sections and forty questions.",
            40,
            40,
        )
        if db.execute(
            "SELECT COUNT(*) AS count FROM questions WHERE mock_id = ?", (mock_id,)
        ).fetchone()["count"] == 0:
            question_number = 1
            for section_index, section in enumerate(pack["sections"], start=1):
                script = _generated_listening_script(section, pack["theme"])
                cursor = db.execute(
                    """
                    INSERT INTO listening_scripts (mock_id, title, script, display_order)
                    VALUES (?, ?, ?, ?)
                    """,
                    (mock_id, section["title"], script, section_index),
                )
                section_questions = _generated_listening_questions(section)
                _create_questions(
                    db,
                    mock_id,
                    section_questions,
                    start_number=question_number,
                    listening_script_id=cursor.lastrowid,
                )
                question_number += len(section_questions)

    db.commit()
