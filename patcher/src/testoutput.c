//#include <unistd.h>
#include <alsa/asoundlib.h>

int main()
{
	snd_seq_t *seq;
    snd_seq_port_info_t *port_info;
	snd_seq_event_t *ev;
	int err1, err2;

    err1 = snd_seq_open(&seq, "default", SND_SEQ_OPEN_DUPLEX, SND_SEQ_NONBLOCK);
    if(err1 < 0)
    {
        printf("Error opening ALSA sequencer\n");
        return 1;
    }

    // set client name
    snd_seq_set_client_name(seq, "Test Client");

    // create a port
    snd_seq_port_info_alloca(&port_info);
    memset(port_info, 0, snd_seq_port_info_sizeof());
    snd_seq_port_info_set_capability(port_info, SND_SEQ_PORT_CAP_READ | SND_SEQ_PORT_CAP_SUBS_READ |
	SND_SEQ_PORT_CAP_WRITE | SND_SEQ_PORT_CAP_SUBS_WRITE);
    snd_seq_port_info_set_type(port_info, SND_SEQ_PORT_TYPE_MIDI_GM | SND_SEQ_PORT_TYPE_APPLICATION | SND_SEQ_PORT_TYPE_MIDI_GENERIC | SND_SEQ_PORT_TYPE_SYNTHESIZER);
    snd_seq_port_info_set_midi_channels(port_info, 16);
    snd_seq_port_info_set_port_specified(port_info, 1);
    snd_seq_port_info_set_name(port_info, "test MIDI port");
    snd_seq_port_info_set_port(port_info, 0);
    err1 = snd_seq_create_port(seq, port_info);

	if(err1  < 0)
	{
		printf("Error creating ALSA sequencer port\n");
		return 1;
	}

//	ev->type = SND_SEQ_EVENT_NOTEON;
//	ev->data.note.channel = 0;
//	ev->data.note.note = 65;
//	ev->data.note.velocity = 100;

	while(1)
	{
		if (snd_seq_event_input(seq, &ev) >= 0)
		{
			snd_seq_ev_set_source(ev, 0);
			snd_seq_ev_set_subs(ev);
			snd_seq_ev_set_direct(ev);
//			sleep(1);
			err1 = snd_seq_event_output(seq, ev);
			err2 = snd_seq_drain_output(seq);
			printf("length %d bufsize %d .. ", snd_seq_event_length(ev), snd_seq_get_output_buffer_size(seq));
			printf("event_output %d, drain_output %d\n", err1, err2);
		}
	}
	
	return 0;
}
