/** 
 * a midi router with extended capabilities:
 *  - routes MIDI messages to a fluid router or synth
 *  - can route a MIDI message to a different type
 *  - recognizing custom rules and routes them to a custom handler
 *  - route messages to MIDI out to talk to external gear
 */

#include "sbmidi.h"



/**
 * Create a new midi router.
 *
 * @param settings Settings used to configure MIDI router
 * @param handler MIDI event callback.
 * @param xhandler passthrough handler for custom rules.
 * @param event_handler_data Caller defined data pointer which gets passed to 'handler'
 * @return New MIDI router instance or NULL on error
 *
 * The new router will start with default rules and therefore pass all events unmodified.
 *
 * The MIDI handler callback should process the possibly filtered/modified MIDI
 * events from the MIDI router and forward them on to a synthesizer for example.
 * The function fluid_synth_handle_midi_event() can be used for \a handle and
 * a #fluid_synth_t passed as the \a event_handler_data parameter for this purpose.
 */
 
sbmidi_router_t *
new_sbmidi_router(int (*custom_handler)(sbmidi_event_t *event, int custom_id),
				  int (*fluid_handler)(void *data, sbmidi_event_t *event),
                  void *fluid_obj)
{
    sbmidi_router_t *router = NULL;

    router = malloc(sizeof(sbmidi_router_t));

    if(router == NULL)
    {
        printf("Out of memory\n");
        return NULL;
    }

    memset(router, 0, sizeof(sbmidi_router_t));

    router->custom_handler = custom_handler;
    router->fluid_handler = fluid_handler;
    router->fluid_obj = fluid_obj;

    // create a default rule which passes all events unmodified
    router->rules = new_sbmidi_router_rule();
    if(!router->rules)
    {
        delete_sbmidi_router(router);
        return NULL;
    }
    
    g_mutex_init(&(router->rules_mutex));

    return router;
}

/**
 * Delete a MIDI router instance.
 * @param router MIDI router to delete
 * @return Returns #SUCCESS on success, #FAILURE otherwise (only if NULL
 *   \a router passed really)
 */
void
delete_sbmidi_router(sbmidi_router_t *router)
{
    sbmidi_router_rule_t *rule;
    sbmidi_router_rule_t *next_rule;

    for(rule = router->rules; rule; rule = next_rule)
    {
        next_rule = rule->next;
        free(rule);
    }

    g_mutex_clear(&(router->rules_mutex));
    free(router);
}

/**
 * Set the output MIDI device for a router instance
 */
void
sbmidi_router_set_midi_device(sbmidi_router_t *router, sbmidi_alsaseq_t *midi_device)
{
    if(midi_device == NULL) return;
    router->midi_device = midi_device;
}

/**
 * Set a MIDI router to use default "unity" rules.
 *
 * @param router Router to set to default rules.
 * @return #SUCCESS on success, #FAILURE otherwise
 *
 * Such a router will pass all events unmodified.
 *
 * @since 1.1.0
 */
int
sbmidi_router_default_rules(sbmidi_router_t *router)
{
    sbmidi_router_rule_t *new_rules;
    sbmidi_router_rule_t *del_rules;
    sbmidi_router_rule_t *rule, *next_rule, *prev_rule;

    /* Allocate new default rules outside of lock */
    new_rules = new_sbmidi_router_rule();
    if(!new_rules)
    {
        delete_sbmidi_router_rule(new_rules);
        return FAILURE;
    }

    g_mutex_lock(&(router->rules_mutex));        /* ++ lock */

        del_rules = NULL;
        prev_rule = NULL;

    // check for rules with pending events, add to delete list if none
    for(rule = router->rules; rule; rule = next_rule)
    {
        next_rule = rule->next;

        if(rule->pending_events == 0)     /* Rule has no pending events? */
        {
            /* Remove rule from rule list */
            if(prev_rule)
            {
                prev_rule->next = next_rule;
            }
            else if(rule == router->rules)
            {
                router->rules = next_rule;
            }

            /* Prepend to delete list */
            rule->next = del_rules;
            del_rules = rule;
        }
        else
        {
            rule->waiting = TRUE;          /* Pending events, mark as waiting */
            prev_rule = rule;
        }
    }

    /* Prepend new default rule */
    new_rules->next = router->rules;
    router->rules = new_rules;

    g_mutex_unlock(&(router->rules_mutex));      /* -- unlock */

    /* Free old rules outside of lock */
    for(rule = del_rules; rule; rule = next_rule)
    {
        next_rule = rule->next;
//		printf("deleting rule: type: %d=%d, chan: %d-%d*%f+%d, par1: %d-%d*%f+%d, par2: %d-%d*%f+%d\n", rule->type, rule->newtype,
//		           rule->chan_min, rule->chan_max, rule->chan_mul, rule->chan_add,
//		           rule->par1_min, rule->par1_max, rule->par1_mul, rule->par1_add,
//		           rule->par2_min, rule->par2_max, rule->par2_mul, rule->par2_add);
				   
        free(rule);
    }
    return SUCCESS;
}

/**
 * Clear all rules in a MIDI router.
 *
 * @param router Router to clear all rules from
 * @return #SUCCESS on success, #FAILURE otherwise
 *
 * An empty router will drop all events until rules are added.
 *
 * @since 1.1.0
 */
int
sbmidi_router_clear_rules(sbmidi_router_t *router)
{
    sbmidi_router_rule_t *del_rules;
    sbmidi_router_rule_t *rule, *next_rule, *prev_rule;
    int i;

    if(router == NULL) return FAILURE;

    g_mutex_lock(&(router->rules_mutex));        /* ++ lock */

        del_rules = NULL;
        prev_rule = NULL;

    // check for rules with pending events, add to delete list if none
    for(rule = router->rules; rule; rule = next_rule)
    {
        next_rule = rule->next;

        if(rule->pending_events == 0)     /* Rule has no pending events? */
        {
            /* Remove rule from rule list */
            if(prev_rule)
            {
                prev_rule->next = next_rule;
            }
            else if(rule == router->rules)
            {
                router->rules = next_rule;
            }

            /* Prepend to delete list */
            rule->next = del_rules;
            del_rules = rule;
        }
        else
        {
            rule->waiting = TRUE;           /* Pending events, mark as waiting */
            prev_rule = rule;
        }
    }

    g_mutex_unlock(&(router->rules_mutex));      /* -- unlock */


    /* Free old rules outside of lock */

    for(rule = del_rules; rule; rule = next_rule)
    {
        next_rule = rule->next;
        free(rule);
    }

    return SUCCESS;
}

/**
 * Add a rule to a MIDI router.
 * @param router MIDI router
 * @param rule Rule to add (used directly and should not be accessed again following a
 *   successful call to this function).
 * @param type The type of rule to add (#sbmidi_router_rule_type)
 * @return #SUCCESS on success, #FAILURE otherwise (invalid rule for example)
 * @since 1.1.0
 */
int
sbmidi_router_add_rule(sbmidi_router_t *router, sbmidi_router_rule_t *rule)
{
    sbmidi_router_rule_t *free_rules, *next_rule;

    if(router == NULL) return FAILURE;
    if(rule == NULL) return FAILURE;

    g_mutex_lock(&(router->rules_mutex));        /* ++ lock */

    /* Take over free rules list, if any (to free outside of lock) */
    free_rules = router->free_rules;
    router->free_rules = NULL;

    rule->next = router->rules;
    router->rules = rule;

    g_mutex_unlock(&(router->rules_mutex));      /* -- unlock */

    /* Free any deactivated rules which were waiting for events and are now done */

    for(; free_rules; free_rules = next_rule)
    {
        next_rule = free_rules->next;
        free(free_rules);
    }
    return SUCCESS;
}

/**
 * Create a new MIDI router rule with default values
 */
sbmidi_router_rule_t *
new_sbmidi_router_rule(void)
{
    sbmidi_router_rule_t *rule;
    rule = malloc(sizeof(sbmidi_router_rule_t));

    if(rule == NULL)
    {
        printf("Out of memory\n");
        return NULL;
    }

    memset(rule, 0, sizeof(sbmidi_router_rule_t));
    rule->chan_max = 999999;
    rule->chan_mul = 1.0;
    rule->par1_max = 999999;
    rule->par1_mul = 1.0;
    rule->par2_max = 999999;
    rule->par2_mul = 1.0;
    rule->custom_id = -1;

    return rule;
};

/**
 * Free a MIDI router rule.
 *
 * @param rule Router rule to free
 *
 * Note that rules which have been added to a router are managed by the router,
 * so this function should seldom be needed.
 *
 * @since 1.1.0
 */
void
delete_sbmidi_router_rule(sbmidi_router_rule_t *rule)
{
    if(rule == NULL) return;
    free(rule);
}

/**
 * Set the channel portion of a rule.
 *
 * @param rule MIDI router rule
 * @param min Minimum value for rule match
 * @param max Maximum value for rule match
 * @param mul Value which is multiplied by matching event's channel value (1.0 to not modify)
 * @param add Value which is added to matching event's channel value (0 to not modify)
 *
 * The \a min and \a max parameters define a channel range window to match
 * incoming events to.  If \a min is less than or equal to \a max then an event
 * is matched if its channel is within the defined range (including \a min
 * and \a max). If \a min is greater than \a max then rule is inverted and matches
 * everything except in *between* the defined range (so \a min and \a max would match).
 *
 * The \a mul and \a add values are used to modify event channel values prior to
 * sending the event, if the rule matches.
 *
 * @since 1.1.0
 */
void
sbmidi_router_rule_set_chan(sbmidi_router_rule_t *rule, int min, int max,
                                float mul, int add)
{
    if(rule == NULL) return;
    rule->chan_min = min;
    rule->chan_max = max;
    rule->chan_mul = mul;
    rule->chan_add = add;
}

/**
 * Set the first parameter portion of a rule.
 *
 * @param rule MIDI router rule
 * @param min Minimum value for rule match
 * @param max Maximum value for rule match
 * @param mul Value which is multiplied by matching event's 1st parameter value (1.0 to not modify)
 * @param add Value which is added to matching event's 1st parameter value (0 to not modify)
 *
 * The 1st parameter of an event depends on the type of event.  For note events
 * its the MIDI note #, for CC events its the MIDI control number, for program
 * change events its the MIDI program #, for pitch bend events its the bend value,
 * for channel pressure its the channel pressure value and for key pressure
 * its the MIDI note number.
 *
 * Pitch bend values have a maximum value of 16383 (8192 is pitch bend center) and all
 * other events have a max of 127.  All events have a minimum value of 0.
 *
 * The \a min and \a max parameters define a parameter range window to match
 * incoming events to.  If \a min is less than or equal to \a max then an event
 * is matched if its 1st parameter is within the defined range (including \a min
 * and \a max). If \a min is greater than \a max then rule is inverted and matches
 * everything except in *between* the defined range (so \a min and \a max would match).
 *
 * The \a mul and \a add values are used to modify event 1st parameter values prior to
 * sending the event, if the rule matches.
 *
 * @since 1.1.0
 */
void
sbmidi_router_rule_set_param1(sbmidi_router_rule_t *rule, int min, int max,
                                  float mul, int add)
{
    if(rule == NULL) return;
    rule->par1_min = min;
    rule->par1_max = max;
    rule->par1_mul = mul;
    rule->par1_add = add;
}

/**
 * Set the second parameter portion of a rule.
 *
 * @param rule MIDI router rule
 * @param min Minimum value for rule match
 * @param max Maximum value for rule match
 * @param mul Value which is multiplied by matching event's 2nd parameter value (1.0 to not modify)
 * @param add Value which is added to matching event's 2nd parameter value (0 to not modify)
 *
 * The 2nd parameter of an event depends on the type of event.  For note events
 * its the MIDI velocity, for CC events its the control value and for key pressure
 * events its the key pressure value.  All other types lack a 2nd parameter.
 *
 * All applicable 2nd parameters have the range 0-127.
 *
 * The \a min and \a max parameters define a parameter range window to match
 * incoming events to.  If \a min is less than or equal to \a max then an event
 * is matched if its 2nd parameter is within the defined range (including \a min
 * and \a max). If \a min is greater than \a max then rule is inverted and matches
 * everything except in *between* the defined range (so \a min and \a max would match).
 *
 * The \a mul and \a add values are used to modify event 2nd parameter values prior to
 * sending the event, if the rule matches.
 *
 * @since 1.1.0
 */
void
sbmidi_router_rule_set_param2(sbmidi_router_rule_t *rule, int min, int max,
                                  float mul, int add)
{
    if(rule == NULL) return;
    rule->par2_min = min;
    rule->par2_max = max;
    rule->par2_mul = mul;
    rule->par2_add = add;
}

/**
 * Set the id for a custom rule
 *
 */
void
sbmidi_router_rule_set_custom(sbmidi_router_rule_t *rule, int id)
{
    if(rule == NULL) return;
    rule->custom_id = id;
}

/**
 * Set the router rule type
 *
 */
void
sbmidi_router_rule_set_type(sbmidi_router_rule_t *rule, sbmidi_event_type type)
{
    if(rule == NULL) return;
    rule->type = type;
}

/**
 * Set the type of midi message generated by a rule
 *
 */
void
sbmidi_router_rule_set_newtype(sbmidi_router_rule_t *rule, sbmidi_event_type type)
{
    if(rule == NULL) return;
    rule->newtype = type;
}

/**
 * Handle a MIDI event through a MIDI router instance.
 * @param data MIDI router instance #sbmidi_router_t, its a void * so that
 *   this function can be used as a callback for other subsystems
 *   (new_sbmidi_driver() for example).
 * @param event MIDI event to handle
 * @return #SUCCESS if all rules were applied successfully, #FAILURE if
 *  an error occurred while applying a rule or (since 2.2.2) the event was
 *  ignored because a parameter was out-of-range after the rule had been applied.
 *  See the note below.
 *
 * Purpose: The midi router is called for each event, that is received
 * via the 'physical' midi input. Each event can trigger an arbitrary number
 * of generated events (one for each rule that matches).
 *
 * In default mode, a noteon event is just forwarded to the synth's 'noteon' function,
 * a 'CC' event to the synth's 'CC' function and so on.
 *
 *
 * @note Each input event has values (ch, par1, par2) that could be changed by a rule.
 * After a rule has been applied on any value and the value is out of range, the event
 * can be either ignored or the value can be clamped depending on the type of the event:
 * - To get full benefice of the rule the value is clamped and the event passed to the output.
 * - To avoid MIDI messages conflicts at the output, the event is ignored
 *   (i.e not passed to the output).
 *   - ch out of range: event is ignored regardless of the event type.
 *   - par1 out of range: event is ignored for PROG_CHANGE or CONTROL_CHANGE type,
 *     par1 is clamped otherwise.
 *   - par2 out of range: par2 is clamped regardless of the event type.
 */
int
sbmidi_router_handle_midi_event(void *data, sbmidi_event_t *event)
{
    sbmidi_router_t *router = (sbmidi_router_t *)data;
    sbmidi_router_rule_t *rule, *next_rule, *prev_rule = NULL;
    sbmidi_event_t new_event;
	int newtype, chan, par1, par2;
    int event_haspar2, newtype_haspar2;

    // convert note-off events to zero-velocity note-on
    if(event->type == NOTE_OFF)
    {
        event->type = NOTE_ON;
        event->param2 = 0;
    }

    // don't change the rules in the middle of what we're doing
    g_mutex_lock(&(router->rules_mutex));

    // select the rule list matching the event type
	if (event->type == NOTE_ON || event->type == NOTE_OFF  ||
	    event->type == CONTROL_CHANGE  || event->type == KEY_PRESSURE)
	{
		event_haspar2=1;
	}
	else if (event->type == PROGRAM_CHANGE || event->type == PITCH_BEND ||
			 event->type == CHANNEL_PRESSURE)
	{
		event_haspar2=0;
	}
	else
    {
		// non-voice message - let other handlers process it
		router->custom_handler(event, -1);
		router->fluid_handler(router->fluid_obj, event);
		g_mutex_unlock(&(router->rules_mutex));
		return SUCCESS;
	}

	// loop over all rules, applying those that match
    for(rule = router->rules; rule; prev_rule = rule, rule = next_rule)
    {
		next_rule = rule->next;
		
		// type check
		if(rule->type && rule->type != event->type) continue;
		
		// channel match check
        if(rule->chan_min > rule->chan_max) {
			// max<min --> skip values in (max, min) range
            if(event->channel > rule->chan_max && event->channel < rule->chan_min) continue;
		} else {
			// min<max --> skip values outside [min, max] range
            if(event->channel > rule->chan_max || event->channel < rule->chan_min) continue;
		}			
		// param1 match check
        if(rule->par1_min > rule->par1_max) {
            if(event->param1 > rule->par1_max && event->param1 < rule->par1_min) continue;
		} else {
            if(event->param1 > rule->par1_max || event->param1 < rule->par1_min) continue;			
		}
		// param2 match check, for applicable events
		if(event_haspar2) { 
			if(rule->par2_min > rule->par2_max) {
				if(event->param2 > rule->par2_max && event->param2 < rule->par2_min) continue;
			} else {
				if(event->param2 > rule->par2_max || event->param2 < rule->par2_min) continue;			
			}
	    }

        // if this is a custom rule, send the event to the custom handler
        if(rule->custom_id > -1)
        {
            router->custom_handler(event, rule->custom_id);
            continue;
        }

		// channel math, skip rule if the new channel is out of range
		chan = rule->chan_add + (int)(event->channel * rule->chan_mul + 0.5);
		if(chan < 0 || chan >= router->midi_device->channels) continue;

		// parameter math, depends on whether event/new event have par2
		newtype = rule->newtype ? rule->newtype : event->type;
		if(newtype == PITCH_BEND || newtype == PROGRAM_CHANGE || newtype == CHANNEL_PRESSURE) newtype_haspar2=0;
		else newtype_haspar2=1;
		
		if(event_haspar2)
	    {
			if(newtype_haspar2)
			{
				par1 = rule->par1_add + (int)(event->param1 * rule->par1_mul + 0.5);
				par2 = rule->par2_add + (int)(event->param2 * rule->par2_mul + 0.5);
			} else { // !newtype_haspar2
				par1 = rule->par2_add + (int)(event->param2 * rule->par2_mul + 0.5);
			}
		} else { // !event_haspar2
			if(!newtype_haspar2)
			{
				par1 = rule->par1_add + (int)(event->param1 * rule->par1_mul + 0.5);
			} else { // newtype_haspar2
				par1 = rule->par2_min;
				par2 = rule->par1_add + (int)(event->param1 * rule->par1_mul + 0.5);
			}
		}			
				
		// skip if new par1 is out of range for CC and PC, clamp otherwise
		if(newtype == CONTROL_CHANGE || newtype == PROGRAM_CHANGE)
        {
            if((par1 < 0) || (par1 > 127)) continue;
        }
        else if(newtype == PITCH_BEND)
        {
            if(par1 < 0) par1 = 0;
			if(par1 > 16383) par1 = 16383;
		} else {
            if(par1 < 0) par1 = 0;
			if(par1 > 127) par1 = 127;
        }
		// clamp par2 for events that have one
		if(newtype_haspar2)
	    {
            if(par2 < 0) par2 = 0;
			if(par2 > 127) par2 = 127;
		}

        /* At this point we have to create an event of event->type on 'chan' with par1 (maybe par2).
         * We keep track of the state of noteon and sustain pedal events. If the application tries
         * to delete a rule, it will only be fully removed, if pending noteoff / pedal off events have
         * arrived. In the meantime while waiting, it will only let through 'negative' events
         * (noteoff or pedal up).
         */
        if((newtype == NOTE_ON && par2 > 0) ||
		   (newtype == CONTROL_CHANGE && (par1 == SUSTAIN_SWITCH || par1 == SOSTENUTO_SWITCH) && par2 >= 64))
        {
            if(rule->keys_cc[par1] == 0)
            {
                rule->keys_cc[par1] = 1; // flag the note/cc and increment the counter
                rule->pending_events++;
            }
        }
        else if((newtype == NOTE_ON && par2 == 0) ||
		        (newtype == CONTROL_CHANGE && (par1 == SUSTAIN_SWITCH || par1 == SOSTENUTO_SWITCH) && par2 < 64))
        {
            if(rule->keys_cc[par1] > 0) // matching negative event found
            {
                rule->keys_cc[par1] = 0; // remove the flag and decrement the counter
                rule->pending_events--;

				// delete the rule if all its negative events have arrived
                if(rule->waiting && rule->pending_events == 0)
                {
					// extract the rule from the rules list
					if(prev_rule) prev_rule->next = next_rule;
					else router->rules = next_rule;
					// prepend the rule to the free list
					rule->next = router->free_rules;
					router->free_rules = rule;
					rule = prev_rule;
                }
            }
        }
		else if(rule->waiting) // inactive except for matching negative events
        {
            continue;
        }
		// create and send the new voice event
		new_event.type = newtype;
		new_event.channel = chan;
        new_event.param1 = par1;
		new_event.param2 = newtype_haspar2 ? par2 : 0;
//		printf("sending type %d chan %d par1 %d par2 %d\n", new_event.type, new_event.channel, new_event.param1, new_event.param2);
		router->fluid_handler(router->fluid_obj, &new_event);
//		if(router->midi_device != NULL) sbmidi_alsaseq_sendevent(router->midi_device, &new_event);
    }
    g_mutex_unlock(&(router->rules_mutex));

	return SUCCESS;
}
