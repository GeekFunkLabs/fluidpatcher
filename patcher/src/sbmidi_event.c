/**
 *  MIDI event API functions
 */

#include "sbmidi.h"


/**
 * Create a MIDI event structure.
 * @return New MIDI event structure or NULL when out of memory.
 */
sbmidi_event_t *
new_sbmidi_event()
{
    sbmidi_event_t *evt;
	evt = malloc(sizeof(sbmidi_event_t));


    if(evt == NULL)
    {
        printf("Out of memory\n");
        return NULL;
    }

    evt->dtime = 0;
    evt->type = 0;
    evt->channel = 0;
    evt->param1 = 0;
    evt->param2 = 0;
    evt->next = NULL;
    evt->paramptr = NULL;
    return evt;
}

/**
 * Delete MIDI event structure.
 * @param evt MIDI event structure
 */
void
delete_sbmidi_event(sbmidi_event_t *evt)
{
	if(evt == NULL) return;
    sbmidi_event_t *temp;

    while(evt)
    {
        temp = evt->next;

        // free sysex data if dynamic (param2)
        if(evt->type == MIDI_SYSEX && evt->paramptr && evt->param2)
        {
            free(evt->paramptr);
        }
        free(evt);
        evt = temp;
    }
}

/**
 * Get the event type field of a MIDI event structure.
 * @param evt MIDI event structure
 * @return Event type field (MIDI status byte without channel)
 */
int
sbmidi_event_get_type(const sbmidi_event_t *evt)
{
    return evt->type;
}

/**
 * Set the event type field of a MIDI event structure.
 * @param evt MIDI event structure
 * @param type Event type field (MIDI status byte without channel)
 */
void
sbmidi_event_set_type(sbmidi_event_t *evt, int type)
{
    evt->type = type;
}

/**
 * Get the channel field of a MIDI event structure.
 * @param evt MIDI event structure
 * @return Channel field
 */
int
sbmidi_event_get_channel(const sbmidi_event_t *evt)
{
    return evt->channel;
}

/**
 * Set the channel field of a MIDI event structure.
 * @param evt MIDI event structure
 * @param chan MIDI channel field
 */
void
sbmidi_event_set_channel(sbmidi_event_t *evt, int chan)
{
    evt->channel = chan;
}

/**
 * Get the param1 field of a MIDI event structure.
 * @param evt MIDI event structure
 * @return MIDI param1 value (0-127)
 */
int
sbmidi_event_get_param1(const sbmidi_event_t *evt)
{
    return evt->param1;
}

/**
 * Set the param1 field of a MIDI event structure.
 * @param evt MIDI event structure
 * @param v MIDI param1 value (0-127)
 */
void
sbmidi_event_set_param1(sbmidi_event_t *evt, int v)
{
    evt->param1 = v;
}

/**
 * Get the param2 field of a MIDI event structure.
 * @param evt MIDI event structure
 * @return MIDI param2 value (0-127)
 */
int
sbmidi_event_get_param2(const sbmidi_event_t *evt)
{
    return evt->param2;
}

/**
 * Set the param2 field of a MIDI event structure.
 * @param evt MIDI event structure
 * @param v MIDI param2 value
 */
void
sbmidi_event_set_param2(sbmidi_event_t *evt, int v)
{
    evt->param2 = v;
}

/**
 * Assign sysex data to a MIDI event structure.
 * @param evt MIDI event structure
 * @param data Pointer to SYSEX data
 * @param size Size of SYSEX data in bytes
 * @param dynamic TRUE if the SYSEX data has been dynamically allocated and
 *   should be freed when the event is freed (only applies if event gets destroyed
 *   with delete_sbmidi_event())
 */
void
sbmidi_event_set_sysex(sbmidi_event_t *evt, void *data, int size, int dynamic)
{
    evt->type = MIDI_SYSEX;
    evt->paramptr = data;
    evt->param1 = size;
    evt->param2 = dynamic;
}
