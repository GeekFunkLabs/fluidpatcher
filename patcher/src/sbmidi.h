/**
 *  midi ALSA driver and event router for squishbox
 */
 
#define ALSA_PCM_NEW_HW_PARAMS_API
#include <alsa/asoundlib.h>
#include <glib.h>
#include <sys/poll.h>

#define SUCCESS 0
#define FAILURE -1

typedef enum
{
    // channel messages
    NOTE_OFF = 0x80,
    NOTE_ON = 0x90,
    KEY_PRESSURE = 0xa0,
    CONTROL_CHANGE = 0xb0,
    PROGRAM_CHANGE = 0xc0,
    CHANNEL_PRESSURE = 0xd0,
    PITCH_BEND = 0xe0,
    // system exclusive
    MIDI_SYSEX = 0xf0,
    // system common
    MIDI_TIME_CODE = 0xf1,
    MIDI_SONG_POSITION = 0xf2,
    MIDI_SONG_SELECT = 0xf3,
    MIDI_TUNE_REQUEST = 0xf6,
    MIDI_EOX = 0xf7,
    // system real-time
    MIDI_SYNC = 0xf8,
    MIDI_TICK = 0xf9,
    MIDI_START = 0xfa,
    MIDI_CONTINUE = 0xfb,
    MIDI_STOP = 0xfc,
    MIDI_ACTIVE_SENSING = 0xfe,
    MIDI_SYSTEM_RESET = 0xff,
    // meta event
    MIDI_META_EVENT = 0xff
} sbmidi_event_type;

#define SUSTAIN_SWITCH 0x40
#define SOSTENUTO_SWITCH 0x42

typedef struct sbmidi_event sbmidi_event_t;
struct sbmidi_event
{
    sbmidi_event_t *next;               // Link to next event
    void *paramptr;                     // Pointer parameter for SYSEX data
    unsigned int dtime;                 // Delay (ticks) between this and previous event. midi tracks.
    unsigned int param1;                // First parameter, or size of SYSEX data
    unsigned int param2;                // Second parameter, or dynamic flag for SYSEX
    unsigned char type;                 // MIDI event type
    unsigned char channel;              // MIDI channel
};

typedef struct sbmidi_router sbmidi_router_t;
typedef struct sbmidi_alsaseq sbmidi_alsaseq_t;
typedef struct sbmidi_router_rule sbmidi_router_rule_t;

typedef struct sbmidi_alsaseq
{
    snd_seq_t *seq_handle;              // handle to alsa sequencer
    snd_seq_addr_t address;             // sequencer client/port address
    int channels;                       // number of MIDI channels
    struct pollfd *pfd;                 // array of poll descriptors
    int npfd;                           // length of poll descriptors array
    GThread *thread;                    // thread the sequencer runs in
    int should_quit;                    // flag to signal the thread to quit
    sbmidi_router_t *router;            // router object that handles midi events
    int autoconnect_inputs;				// flag
    int autoconnect_outputs;            // flag
} sbmidi_alsaseq_t;

typedef struct sbmidi_router_rule
{
    sbmidi_event_type type;             // event type to catch
    sbmidi_event_type newtype;          // type for the routed midi message, default is NULL = same as rule type

    int chan_min;                       // Channel window, for which this rule is valid
    int chan_max;
    double chan_mul;                    // Channel multiplier
    int chan_add;                       // Channel offset

    int par1_min;                       // Parameter 1 window and conversion
    int par1_max;
    double par1_mul;
    int par1_add;

    int par2_min;                       // Parameter 2 window and conversion
    int par2_max;
    double par2_mul;
    int par2_add;

    int pending_events;                 // counter for how many notes or pedals have been held by this rule
    char keys_cc[128];                  // flags which notes or sustain/sostenuto pedals are held
    int waiting;                        // flag to block deletion until associated notes/sustain/sostenuto have been ended

    int custom_id;                      // for custom rules, a rule id for the custom handler, default -1 is standard routing

    sbmidi_router_rule_t *next;         // next rule in the list
} sbmidi_router_rule_t;

typedef struct sbmidi_router
{
    sbmidi_router_rule_t *rules;        // List of rules
    sbmidi_router_rule_t *free_rules;   // List of rules to free
    sbmidi_alsaseq_t *midi_device;      // MIDI output device
    // handler for custom rules
    int (*custom_handler)(sbmidi_event_t *event, int custom_id);
	// fluidsynth function for generated events
    int (*fluid_handler)(void *data, sbmidi_event_t *event);
	void *fluid_obj;				                       // linking object for the fluid handler     
    GMutex rules_mutex;
} sbmidi_router_t;

sbmidi_alsaseq_t *
new_sbmidi_alsaseq(int midi_channels, int autoconnect_inputs, int autoconnect_outputs, sbmidi_router_t *router);
void delete_sbmidi_alsaseq(sbmidi_alsaseq_t *p);
void sbmidi_alsaseq_sendevent(sbmidi_alsaseq_t *dev, sbmidi_event_t *event);

sbmidi_router_t *
new_sbmidi_router(int (*custom_handler)(sbmidi_event_t *event, int custom_id),
				  int (*fluid_handler)(void *data, sbmidi_event_t *event),
                  void *fluid_obj);
void delete_sbmidi_router(sbmidi_router_t *router);
void sbmidi_router_set_midi_device(sbmidi_router_t *router, sbmidi_alsaseq_t *midi_device);
int sbmidi_router_default_rules(sbmidi_router_t *router);
int sbmidi_router_clear_rules(sbmidi_router_t *router);
int sbmidi_router_add_rule(sbmidi_router_t *router, sbmidi_router_rule_t *rule);
int sbmidi_router_handle_midi_event(void *data, sbmidi_event_t *event);

sbmidi_router_rule_t *new_sbmidi_router_rule(void);
void delete_sbmidi_router_rule(sbmidi_router_rule_t *rule);
void sbmidi_router_rule_set_chan(sbmidi_router_rule_t *rule,
                                 int min, int max, float mul, int add);
void sbmidi_router_rule_set_param1(sbmidi_router_rule_t *rule,
                                   int min, int max, float mul, int add);
void sbmidi_router_rule_set_param2(sbmidi_router_rule_t *rule,
                                   int min, int max, float mul, int add);
void sbmidi_router_rule_set_custom(sbmidi_router_rule_t *rule, int id);
void sbmidi_router_rule_set_newtype(sbmidi_router_rule_t *rule, sbmidi_event_type type);

sbmidi_event_t *new_sbmidi_event(void);
void delete_sbmidi_event(sbmidi_event_t *evt);
int sbmidi_event_get_type(const sbmidi_event_t *evt);
void sbmidi_event_set_type(sbmidi_event_t *evt, int type);
int sbmidi_event_get_channel(const sbmidi_event_t *evt);
void sbmidi_event_set_channel(sbmidi_event_t *evt, int chan);
int sbmidi_event_get_param1(const sbmidi_event_t *evt);
void sbmidi_event_set_param1(sbmidi_event_t *evt, int v);
int sbmidi_event_get_param2(const sbmidi_event_t *evt);
void sbmidi_event_set_param2(sbmidi_event_t *evt, int v);
void sbmidi_event_set_sysex(sbmidi_event_t *evt, void *data, int size, int dynamic);
